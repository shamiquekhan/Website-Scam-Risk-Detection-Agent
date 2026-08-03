from app.models import SignalResult, ScanRequest, ScanResult
from datetime import datetime, timezone


def test_signal_result():
    s = SignalResult(
        signal_name="ssl_check",
        category="ssl",
        passed=True,
        deduction=0,
        detail="SSL cert valid",
    )
    assert s.signal_name == "ssl_check"
    assert s.passed is True
    assert s.available is True


def test_signal_result_unavailable():
    s = SignalResult(
        signal_name="whois_check",
        category="domain_trust",
        passed=True,
        deduction=0,
        detail="Unavailable",
        available=False,
    )
    assert s.available is False


def test_scan_request():
    r = ScanRequest(url="https://example.com")
    assert r.url == "https://example.com"


def test_scan_result():
    r = ScanResult(
        scan_id="test-123",
        url="https://example.com",
        normalized_domain="example.com",
        score=85,
        verdict="Safe",
        summary="All clear.",
        signals=[],
        scanned_at=datetime.now(timezone.utc),
    )
    assert r.score == 85
    assert r.verdict == "Safe"
    assert r.cached is False
