import asyncio
import os
import time

import httpx

from app.models import SignalResult
from app.scoring.engine import _load_weights
from app.utils import _normalize_entry, url_in_feed

URLHAUS_LOOKUP_URL = "https://urlhaus-api.abuse.ch/v1/url/"
URLHAUS_BLOCKLIST_URL = "https://urlhaus.abuse.ch/downloads/text_online/"
BLOCKLIST_REFRESH_SECONDS = 24 * 3600
BLOCKLIST_FILE = os.path.join(os.path.dirname(__file__), "../../data/urlhaus_blocklist.txt")

_feed_cache: set[str] | None = None
_feed_fetched_at: float = 0.0
_feed_refreshing = False


def _parse_blocklist(text: str) -> set[str]:
    entries = set()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        key = _normalize_entry(line)
        if key:
            entries.add(key)
    return entries


def _load_blocklist_from_disk() -> set[str] | None:
    try:
        if os.path.exists(BLOCKLIST_FILE) and os.path.getsize(BLOCKLIST_FILE) > 0:
            with open(BLOCKLIST_FILE) as f:
                return _parse_blocklist(f.read())
    except Exception:
        pass
    return None


async def _refresh_blocklist() -> None:
    global _feed_cache, _feed_fetched_at, _feed_refreshing
    if _feed_refreshing:
        return
    _feed_refreshing = True
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(URLHAUS_BLOCKLIST_URL)
            if resp.status_code == 200:
                _feed_cache = _parse_blocklist(resp.text)
                _feed_fetched_at = time.time()
                try:
                    with open(BLOCKLIST_FILE, "w") as f:
                        f.write(resp.text)
                except Exception:
                    pass
    except Exception:
        pass
    finally:
        _feed_refreshing = False


async def get_blocklist() -> set[str]:
    global _feed_cache, _feed_fetched_at
    if _feed_cache is None:
        _feed_cache = _load_blocklist_from_disk()
    if _feed_cache is None:
        await _refresh_blocklist()
    elif (time.time() - _feed_fetched_at) > BLOCKLIST_REFRESH_SECONDS:
        await _refresh_blocklist()
    return _feed_cache or set()


async def check(domain_or_url: str) -> SignalResult:
    auth_key = os.getenv("URLHAUS_AUTH_KEY", "")
    weights = _load_weights()

    if not auth_key:
        return await _check_blocklist(domain_or_url, weights)

    payload = {"url": domain_or_url}
    headers = {"Auth-Key": auth_key}
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.post(URLHAUS_LOOKUP_URL, headers=headers, data=payload)
            if resp.status_code == 409:
                return _hit(weights)
            if resp.status_code == 404:
                return _clean("URL not found in the URLhaus malware/phishing database.")
            if resp.status_code != 200:
                raise ValueError(f"URLhaus returned {resp.status_code}")
            result = resp.json()
    except Exception:
        return SignalResult(
            signal_name="urlhaus",
            category="reputation",
            passed=True,
            deduction=0,
            detail="URLhaus check could not be completed.",
            available=False,
        )

    if result.get("query_status") == "no_results":
        return _clean("URL not found in the URLhaus malware/phishing database.")
    if result.get("blacklist_status") == "not_blacklisted" and result.get("url_status") in ("online", "offline"):
        return _clean("URL not blacklisted in URLhaus.")
    return _hit(weights)


async def _check_blocklist(domain_or_url: str, weights: dict) -> SignalResult:
    try:
        blocklist = await asyncio.wait_for(get_blocklist(), timeout=35)
    except Exception:
        return SignalResult(
            signal_name="urlhaus",
            category="reputation",
            passed=True,
            deduction=0,
            detail="URLhaus blocklist could not be loaded.",
            available=False,
            availability_reason="blocklist_unavailable",
        )

    if not blocklist:
        return SignalResult(
            signal_name="urlhaus",
            category="reputation",
            passed=True,
            deduction=0,
            detail="URLhaus blocklist is empty.",
            available=False,
            availability_reason="blocklist_empty",
        )

    if url_in_feed(domain_or_url, blocklist):
        return _hit(weights, feed_size=len(blocklist))
    return _clean(f"URL not found in the URLhaus blocklist ({len(blocklist)} entries cached).")


def _hit(weights: dict, feed_size: int | None = None) -> SignalResult:
    detail = "URL flagged in the URLhaus malware/phishing database."
    if feed_size is not None:
        detail += f" ({feed_size} entries cached)."
    return SignalResult(
        signal_name="urlhaus",
        category="reputation",
        passed=False,
        deduction=weights.get("urlhaus_hit", 35),
        detail=detail,
    )


def _clean(detail: str) -> SignalResult:
    return SignalResult(
        signal_name="urlhaus",
        category="reputation",
        passed=True,
        deduction=0,
        detail=detail,
    )