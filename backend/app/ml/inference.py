import os

import numpy as np

from app.ml.feature_extractor import extract_features, FEATURE_COUNT

MODEL_PATH = os.path.join(os.path.dirname(__file__), "../../models/phishing_classifier.onnx")

_session = None
_load_error: str | None = None


def model_available() -> bool:
    return _get_session() is not None


def classify(url: str) -> float:
    """Return phishing probability in [0, 1] from the local ONNX classifier.

    Raises RuntimeError if the model is not available.
    """
    session = _get_session()
    if session is None:
        raise RuntimeError(f"ONNX model not available: {_load_error or 'model file missing'}")

    features = np.array([extract_features(url)], dtype=np.float32)
    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: features})

    probability = _extract_probability(outputs)
    if probability is None:
        raise RuntimeError("ONNX model output shape was unexpected")
    return probability


def _extract_probability(outputs: list) -> float | None:
    """Handle both dense (N,2) probability tensors and seq(map) tree outputs."""
    for out in outputs:
        if isinstance(out, list):
            for entry in out:
                if isinstance(entry, dict) and 1 in entry:
                    return float(entry[1])
        if isinstance(out, dict) and 1 in out:
            return float(out[1])
        arr = np.asarray(out, dtype=object)
        if arr.ndim == 2 and arr.shape == (1, 2):
            return float(arr[0][1])
    return None


def _get_session():
    global _session, _load_error
    if _session is not None:
        return _session
    if _load_error:
        return None
    try:
        import onnxruntime as ort
    except ImportError:
        _load_error = "onnxruntime not installed"
        return None

    if not os.path.exists(MODEL_PATH):
        _load_error = f"model file not found at {MODEL_PATH}"
        return None

    try:
        _session = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])
    except Exception as exc:
        _load_error = str(exc)
        return None
    return _session