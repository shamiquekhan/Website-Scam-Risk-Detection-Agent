from app.models import SignalResult
from app.ml import inference
from app.scoring.engine import _load_weights

THRESHOLD_HIGH = 0.8
THRESHOLD_MEDIUM = 0.6


async def check(domain_or_url: str) -> SignalResult:
    if not inference.model_available():
        return SignalResult(
            signal_name="local_ml",
            category="ml",
            passed=True,
            deduction=0,
            detail="Local ML classifier unavailable (model not loaded).",
            available=False,
            availability_reason="model_unavailable",
        )

    weights = _load_weights()
    try:
        probability = inference.classify(domain_or_url)
    except Exception:
        return SignalResult(
            signal_name="local_ml",
            category="ml",
            passed=True,
            deduction=0,
            detail="Local ML classifier could not run.",
            available=False,
            availability_reason="inference_error",
        )

    if probability >= THRESHOLD_HIGH:
        return SignalResult(
            signal_name="local_ml",
            category="ml",
            passed=False,
            deduction=weights.get("local_ml_high", 30),
            detail=f"Local ML classifier flags strong phishing indicators (confidence {probability:.0%}).",
            raw_data={"probability": probability},
        )

    if probability >= THRESHOLD_MEDIUM:
        return SignalResult(
            signal_name="local_ml",
            category="ml",
            passed=False,
            deduction=weights.get("local_ml_medium", 15),
            detail=f"Local ML classifier found moderate phishing indicators (confidence {probability:.0%}).",
            raw_data={"probability": probability},
        )

    return SignalResult(
        signal_name="local_ml",
        category="ml",
        passed=True,
        deduction=0,
        detail=f"Local ML classifier found no phishing indicators (confidence {probability:.0%}).",
        raw_data={"probability": probability},
    )