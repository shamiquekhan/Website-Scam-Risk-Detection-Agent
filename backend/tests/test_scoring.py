from app.models import SignalResult
from app.scoring.engine import calculate_assessment, calculate_score


def test_all_pass():
    signals = [
        SignalResult(signal_name="ssl_check", category="ssl", passed=True, deduction=0, detail="OK"),
        SignalResult(signal_name="whois_check", category="domain_trust", passed=True, deduction=0, detail="OK"),
    ]
    score, verdict = calculate_score(signals)
    assert score == 100
    assert verdict == "Safe"


def test_moderate_deductions():
    signals = [
        SignalResult(signal_name="whois_check", category="domain_trust", passed=False, deduction=25, detail="New domain"),
        SignalResult(signal_name="typosquat", category="brand", passed=False, deduction=30, detail="Typosquat"),
    ]
    score, verdict = calculate_score(signals)
    assert score == 45
    assert verdict == "High Risk"


def test_blacklist_cap():
    signals = [
        SignalResult(signal_name="safe_browsing", category="reputation", passed=False, deduction=40, detail="Blacklisted"),
        SignalResult(signal_name="ssl_check", category="ssl", passed=True, deduction=0, detail="Valid SSL"),
    ]
    score, verdict = calculate_score(signals)
    assert score <= 40
    assert verdict == "High Risk"


def test_caution_band():
    signals = [
        SignalResult(signal_name="whois_check", category="domain_trust", passed=False, deduction=25, detail="New domain"),
        SignalResult(signal_name="content_heuristics", category="content", passed=False, deduction=12, detail="Redirect"),
    ]
    score, verdict = calculate_score(signals)
    assert 50 <= score <= 79
    assert verdict == "Caution"


def test_unavailable_excluded():
    signals = [
        SignalResult(signal_name="safe_browsing", category="reputation", passed=False, deduction=40, detail="Unavailable", available=False),
        SignalResult(signal_name="ssl_check", category="ssl", passed=True, deduction=0, detail="OK"),
    ]
    score, verdict = calculate_score(signals)
    assert score == 100
    assert verdict == "Safe"


def test_old_domain_bonus():
    signals = [
        SignalResult(
            signal_name="whois_check",
            category="domain_trust",
            passed=True,
            deduction=0,
            detail="Old domain",
            raw_data={"days_old": 1000, "privacy_protected": False},
        ),
        SignalResult(signal_name="ssl_check", category="ssl", passed=True, deduction=0, detail="Valid"),
        SignalResult(signal_name="safe_browsing", category="reputation", passed=True, deduction=0, detail="Clean"),
        SignalResult(signal_name="urlhaus", category="reputation", passed=True, deduction=0, detail="Clean"),
    ]
    score, verdict = calculate_score(signals)
    assert score == 100
    assert verdict == "Safe"


def test_privacy_whois_is_scored_with_password_form():
    signals = [
        SignalResult(
            signal_name="whois_check",
            category="domain_trust",
            passed=True,
            deduction=0,
            detail="Privacy protected",
            raw_data={"days_old": 500, "privacy_protected": True},
        ),
        SignalResult(
            signal_name="content_heuristics",
            category="content",
            passed=True,
            deduction=0,
            detail="Password form",
            raw_data={"has_password_form": True},
        ),
    ]
    score, verdict = calculate_score(signals)
    assert score == 92
    assert verdict == "Safe"


def test_insufficient_data_has_no_score():
    signals = [
        SignalResult(signal_name="ssl_check", category="ssl", passed=False, deduction=20, detail="Failed"),
        SignalResult(signal_name="dns_hosting", category="hosting", passed=False, deduction=25, detail="No DNS"),
        SignalResult(signal_name="typosquat", category="brand", passed=True, deduction=0, detail="Clean"),
        SignalResult(signal_name="whois_check", category="domain_trust", passed=True, deduction=0, detail="Unavailable", available=False),
        SignalResult(signal_name="content_heuristics", category="content", passed=True, deduction=0, detail="Unavailable", available=False),
        SignalResult(signal_name="safe_browsing", category="reputation", passed=True, deduction=0, detail="Not configured", available=False),
        SignalResult(signal_name="virustotal", category="reputation", passed=True, deduction=0, detail="Not configured", available=False),
        SignalResult(signal_name="urlhaus", category="reputation", passed=True, deduction=0, detail="Unavailable", available=False),
    ]
    score, verdict, completed, total, confidence = calculate_assessment(signals)
    assert score is None
    assert verdict == "Insufficient Data"
    assert completed == 3
    assert total == 8
    assert confidence == 38


def test_completeness_reduces_confident_score():
    signals = [
        SignalResult(signal_name=f"signal_{index}", category="test", passed=True, deduction=0, detail="OK")
        for index in range(5)
    ] + [
        SignalResult(signal_name=f"missing_{index}", category="test", passed=True, deduction=0, detail="Missing", available=False)
        for index in range(3)
    ]
    score, verdict, completed, total, confidence = calculate_assessment(signals)
    assert score == 62
    assert verdict == "Caution"
    assert completed == 5
    assert total == 8
    assert confidence == 62
