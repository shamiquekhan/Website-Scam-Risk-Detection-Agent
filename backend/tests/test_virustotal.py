from app.collectors.virustotal import assess_stats, _is_top_brand


def test_clean_is_passed():
    passed, deduction, _, _ = assess_stats(0, 0, False)
    assert passed is True
    assert deduction == 0


def test_brand_with_single_flag_is_not_deducted():
    passed, deduction, _, _ = assess_stats(0, 1, True)
    assert passed is True
    assert deduction == 0


def test_three_plus_flags_is_heavy_regardless_of_brand():
    passed, deduction, _, _ = assess_stats(2, 2, True)
    assert passed is False
    assert deduction == 30


def test_single_malicious_non_brand_deducts_noise_level():
    passed, deduction, _, _ = assess_stats(1, 0, False)
    assert passed is False
    assert deduction == 10


def test_single_suspicious_non_brand_is_low_deduction():
    passed, deduction, _, _ = assess_stats(0, 1, False)
    assert passed is False
    assert deduction == 5


def test_top_brand_recognition():
    assert _is_top_brand("https://google.com/") is True
    assert _is_top_brand("https://scholar.google.com/") is True
    assert _is_top_brand("https://not-a-brand.example.co/") is False