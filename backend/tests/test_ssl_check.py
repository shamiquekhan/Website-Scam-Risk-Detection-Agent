import pytest

from app.collectors import ssl_check


@pytest.mark.asyncio
async def test_https_connection_failure_is_scored(monkeypatch):
    def fail_connection(*args, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(ssl_check.socket, "create_connection", fail_connection)

    result = await ssl_check.check("https://example.com")

    assert result.available is True
    assert result.passed is False
    assert result.deduction == 20
