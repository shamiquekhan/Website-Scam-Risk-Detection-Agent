import json
import os
from app.models import SignalResult

_weights: dict[str, int] | None = None

BLACKLIST_SIGNALS = ("safe_browsing", "urlhaus", "openphish")


def _load_weights() -> dict[str, int]:
    global _weights
    if _weights is None:
        path = os.path.join(os.path.dirname(__file__), "weights.json")
        with open(path) as f:
            _weights = json.load(f)
    return _weights


def verdict_for(score: int) -> str:
    if score >= 90:
        return "Safe"
    if score >= 70:
        return "Likely Safe"
    if score >= 50:
        return "Caution"
    if score >= 30:
        return "Suspicious"
    return "High Risk"


def calculate_score(signals: list[SignalResult]) -> tuple[int, str]:
    weights = _load_weights()
    score = 100
    has_blacklist_hit = False
    available = {s.signal_name: s for s in signals if s.available}

    for signal in available.values():
        score -= signal.deduction
        if signal.signal_name in BLACKLIST_SIGNALS and not signal.passed:
            has_blacklist_hit = True

    whois = available.get("whois_check")
    content = available.get("content_heuristics")
    if (
        whois
        and content
        and whois.raw_data
        and whois.raw_data.get("privacy_protected")
        and content.raw_data
        and content.raw_data.get("has_password_form")
    ):
        score -= weights.get("privacy_protected_whois", 8)

    if (
        whois
        and whois.raw_data
        and whois.raw_data.get("days_old", 0) > 730
        and available.get("ssl_check")
        and available["ssl_check"].passed
        and all(
            available.get(sig) and available[sig].passed
            for sig in ("safe_browsing", "urlhaus", "openphish")
        )
    ):
        score += weights.get("positive_bonus_old_domain", 5)

    if has_blacklist_hit:
        score = min(score, 29)

    score = max(0, min(100, score))
    return score, verdict_for(score)


MIN_COMPLETED_SIGNALS = 6


def calculate_assessment(signals: list[SignalResult]) -> tuple[int | None, str, int, int, int]:
    raw_score, _ = calculate_score(signals)
    total_signals = len(signals)
    completed_signals = sum(1 for signal in signals if signal.available)
    confidence = round((completed_signals / total_signals) * 100) if total_signals else 0

    if completed_signals < MIN_COMPLETED_SIGNALS:
        return None, "Insufficient Data", completed_signals, total_signals, confidence

    adjusted_score = round(raw_score * completed_signals / total_signals)
    adjusted_score = max(0, min(100, adjusted_score))
    return adjusted_score, verdict_for(adjusted_score), completed_signals, total_signals, confidence