"""Export the trained sklearn model to ONNX for lightweight on-device inference."""

import pickle
from pathlib import Path

import numpy as np
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

from app.ml.feature_extractor import FEATURE_COUNT

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_PKL = MODEL_DIR / "phishing_classifier.pkl"
MODEL_ONNX = MODEL_DIR / "phishing_classifier.onnx"


def export() -> Path:
    if not MODEL_PKL.exists():
        raise RuntimeError(f"Trained model not found at {MODEL_PKL}. Run `python -m ml_training.train` first.")
    with MODEL_PKL.open("rb") as f:
        model = pickle.load(f)

    onnx_model = convert_sklearn(
        model,
        initial_types=[("X", FloatTensorType([None, FEATURE_COUNT]))],
        target_opset=17,
    )
    MODEL_ONNX.write_bytes(onnx_model.SerializeToString())
    print(f"Exported -> {MODEL_ONNX} ({MODEL_ONNX.stat().st_size} bytes)")

    _verify()
    return MODEL_ONNX


def _verify() -> None:
    import onnxruntime as ort

    session = ort.InferenceSession(str(MODEL_ONNX), providers=["CPUExecutionProvider"])
    sample = np.zeros((1, FEATURE_COUNT), dtype=np.float32)
    outputs = session.run(None, {session.get_inputs()[0].name: sample})
    print(f"ONNX verified. Output tensors: {[np.asarray(o).shape for o in outputs]}")


if __name__ == "__main__":
    export()