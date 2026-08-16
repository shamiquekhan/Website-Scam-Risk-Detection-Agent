from app.collectors.openphish import _parse_feed


def test_parse_feed_extracts_normalized_entries():
    text = (
        "http://fidelity-investment.vercel.app/\n"
        "https://www.roblox.com.mu/communities/1\n"
        "http://example.co.uk/login\n"
        "\n"
    )
    feed = _parse_feed(text)
    assert "fidelity-investment.vercel.app/" in feed
    assert "www.roblox.com.mu/communities/1" in feed
    assert "example.co.uk/login" in feed


def test_parse_feed_empty():
    assert _parse_feed("") == set()
    assert _parse_feed("\n\n") == set()