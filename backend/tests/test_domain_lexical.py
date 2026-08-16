from app.collectors.domain_lexical import check


async def test_clean_domain_passes():
    result = await check("https://example.com/")
    assert result.passed is True
    assert result.deduction == 0
    assert result.available is True


async def test_suspicious_tld_deducts():
    result = await check("https://something.tk/login")
    assert result.passed is False
    assert result.deduction >= 10
    assert "tk" in result.detail


async def test_at_sign_in_netloc_deducts():
    result = await check("https://paypal.com@evil.com/login")
    assert result.passed is False
    assert result.deduction >= 15


async def test_high_entropy_host_deducts():
    result = await check("https://a3f9x2kz1b8q7w5v4n2m9c0x.xyz/")
    assert result.passed is False
    assert result.deduction >= 5