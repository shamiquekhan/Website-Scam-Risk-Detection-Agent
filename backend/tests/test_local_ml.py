from app.ml import inference
from app.ml.feature_extractor import (
    SUSPICIOUS_TLDS,
    FEATURE_COUNT,
    extract_features,
)


def test_feature_vector_length():
    features = extract_features("https://example.com/path?q=1")
    assert len(features) == FEATURE_COUNT


def test_features_flag_ip_literal():
    features = extract_features("http://192.168.1.1/login")
    assert features[7] == 1.0


def test_features_flag_suspicious_tld():
    features = extract_features("https://secure-login-account.tk/")
    assert features[10] == 1.0


def test_features_https_flag():
    assert extract_features("https://example.com")[8] == 1.0
    assert extract_features("http://example.com")[8] == 0.0


def test_suspicious_tlds_contains_known_bad_tlds():
    assert {"tk", "ml", "cf", "ga", "gq", "xyz"} <= SUSPICIOUS_TLDS


def test_classify_clean_site_low_risk():
    assert inference.classify("https://github.com/") < 0.4


def test_classify_phishing_pattern_high_risk():
    assert inference.classify("https://secure-login-paypal-account.tk/login") > 0.6


def test_model_available():
    assert inference.model_available() is True