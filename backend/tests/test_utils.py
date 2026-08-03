import pytest
from app.utils import normalize_url, extract_domain


def test_normalize_adds_scheme():
    assert normalize_url("example.com").startswith("https://")


def test_normalize_keeps_https():
    assert normalize_url("https://example.com") == "https://example.com/"


def test_normalize_strips_whitespace():
    assert normalize_url("  https://test.com  ") == "https://test.com/"


def test_normalize_rejects_javascript():
    with pytest.raises(ValueError, match="Unsupported URL scheme"):
        normalize_url("javascript:alert(1)")


def test_extract_domain_simple():
    assert extract_domain("https://www.example.com") == "example.com"


def test_extract_domain_subdomain():
    assert extract_domain("https://sub.example.co.uk") == "example.co.uk"
