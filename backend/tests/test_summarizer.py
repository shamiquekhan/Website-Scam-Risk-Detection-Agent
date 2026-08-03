from datetime import datetime, timezone

from app.llm.summarizer import fallback_summary
from app.models import ScanResult, SignalResult


def _scan_result(verdict, signals, score=None, completed=0, total=8, confidence=0):
    return ScanResult(
        scan_id="test",
        url="https://example.com",
        normalized_domain="example.com",
        score=score,
        verdict=verdict,
        summary="",
        signals=signals,
        scanned_at=datetime.now(timezone.utc),
        completed_signals=completed,
        total_signals=total,
        confidence=confidence,
    )


def test_insufficient_data_summary_leads_with_absence():
    signals = [
        SignalResult(signal_name="ssl_check", category="ssl", passed=True, deduction=0, detail="valid"),
        SignalResult(signal_name="whois_check", category="domain_trust", passed=True, deduction=0, detail="unavailable", available=False),
        SignalResult(signal_name="dns_hosting", category="hosting", passed=True, deduction=0, detail="unavailable", available=False),
        SignalResult(signal_name="safe_browsing", category="reputation", passed=True, deduction=0, detail="not configured", available=False),
        SignalResult(signal_name="virustotal", category="reputation", passed=True, deduction=0, detail="not configured", available=False),
        SignalResult(signal_name="urlhaus", category="reputation", passed=True, deduction=0, detail="not configured", available=False),
        SignalResult(signal_name="content_heuristics", category="content", passed=True, deduction=0, detail="clean"),
        SignalResult(signal_name="typosquat", category="brand", passed=True, deduction=0, detail="clean"),
    ]
    result = _scan_result("Insufficient Data", signals, score=None, completed=3, total=8, confidence=38)
    summary = fallback_summary(result)
    assert summary.startswith("Only 3 of 8 checks completed")
    assert "reputation" in summary or "hosting" in summary
    assert "No red flags were found across all checks performed." not in summary
    assert "unverified" in summary


def test_safe_verdict_still_uses_clean_message():
    signals = [
        SignalResult(signal_name="ssl_check", category="ssl", passed=True, deduction=0, detail="valid"),
        SignalResult(signal_name="whois_check", category="domain_trust", passed=True, deduction=0, detail="old"),
    ]
    result = _scan_result("Safe", signals, score=100, completed=2, total=2, confidence=100)
    summary = fallback_summary(result)
    assert "No red flags were found across all checks performed." in summary
