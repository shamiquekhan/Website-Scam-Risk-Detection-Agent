"""Evaluate the trained model on held-out data with detailed metrics."""

import pickle
from pathlib import Path

import numpy as np
from sklearn.metrics import (
    classification_report,
    precision_recall_curve,
    roc_auc_score,
)

from ml_training.features import build_dataset, build_feature_matrix
from ml_training.train import MODEL_PKL

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"


def evaluate(max_per_class: int = 8000, seed: int = 42):
    with MODEL_PKL.open("rb") as f:
        model = pickle.load(f)

    urls, labels = build_dataset(max_per_class=max_per_class, seed=seed + 1)
    X = build_feature_matrix(urls)
    y = np.array(labels)

    proba = model.predict_proba(X)[:, 1]
    y_pred = model.predict(X)

    print("=== Classification report ===")
    print(classification_report(y, y_pred, target_names=["legit", "phishing"], digits=3))
    print(f"ROC-AUC: {roc_auc_score(y, proba):.3f}")

    precision, recall, thresholds = precision_recall_curve(y, proba)
    for target_precision in (0.90, 0.95):
        idx = next(i for i, p in enumerate(precision) if p <= target_precision)
        print(
            f"At precision ~{target_precision:.2f}: threshold={thresholds[idx]:.3f}, recall={recall[idx]:.3f}"
        )
    return model


if __name__ == "__main__":
    evaluate()