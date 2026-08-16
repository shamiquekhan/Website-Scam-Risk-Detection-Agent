"""Train the phishing classifier (Random Forest) and report metrics."""

import os
import pickle
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
from sklearn.model_selection import train_test_split

from ml_training.features import build_dataset, build_feature_matrix

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_PKL = MODEL_DIR / "phishing_classifier.pkl"
MODEL_ONNX = MODEL_DIR / "phishing_classifier.onnx"


def train(max_per_class: int = 8000, test_size: float = 0.2, seed: int = 42):
    print("Building dataset (OpenPhish + synthetic positives, Majestic negatives)...")
    urls, labels = build_dataset(max_per_class=max_per_class, seed=seed)
    X = build_feature_matrix(urls)
    y = np.array(labels)
    print(f"Dataset: {len(urls)} samples, {int(sum(y))} phishing / {int(len(y) - sum(y))} legit")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y
    )

    print("Training RandomForestClassifier...")
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=18,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=seed,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    with MODEL_PKL.open("wb") as f:
        pickle.dump(model, f)
    print(f"Saved model -> {MODEL_PKL}")

    y_pred = model.predict(X_test)
    print("\n--- Holdout evaluation ---")
    print(f"Precision (phishing): {precision_score(y_test, y_pred):.3f}")
    print(f"Recall    (phishing): {recall_score(y_test, y_pred):.3f}")
    print(f"F1        (phishing): {f1_score(y_test, y_pred):.3f}")
    print("Confusion matrix (TN FP / FN TP):")
    print(confusion_matrix(y_test, y_pred))
    return model


if __name__ == "__main__":
    train()