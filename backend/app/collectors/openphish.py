import asyncio
import os
import time

import httpx

from app.models import SignalResult
from app.scoring.engine import _load_weights
from app.utils import _normalize_entry, url_in_feed

FEED_URL = "https://openphish.com/feed.txt"
FEED_REFRESH_SECONDS = 6 * 3600
FEED_FILE = os.path.join(os.path.dirname(__file__), "../../data/openphish_feed.txt")

_feed_cache: set[str] | None = None
_feed_fetched_at: float = 0.0
_feed_refreshing = False


def _parse_feed(text: str) -> set[str]:
    entries = set()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        key = _normalize_entry(line)
        if key:
            entries.add(key)
    return entries


def _load_feed_from_disk() -> set[str] | None:
    try:
        if os.path.exists(FEED_FILE) and os.path.getsize(FEED_FILE) > 0:
            with open(FEED_FILE) as f:
                return _parse_feed(f.read())
    except Exception:
        pass
    return None


async def _refresh_feed() -> None:
    global _feed_cache, _feed_fetched_at, _feed_refreshing
    if _feed_refreshing:
        return
    _feed_refreshing = True
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(FEED_URL)
            if resp.status_code == 200:
                _feed_cache = _parse_feed(resp.text)
                _feed_fetched_at = time.time()
                try:
                    with open(FEED_FILE, "w") as f:
                        f.write(resp.text)
                except Exception:
                    pass
    except Exception:
        pass
    finally:
        _feed_refreshing = False


def _feed_stale() -> bool:
    return _feed_cache is None or (time.time() - _feed_fetched_at) > FEED_REFRESH_SECONDS


async def get_feed() -> set[str]:
    global _feed_cache, _feed_fetched_at
    if _feed_cache is None:
        _feed_cache = _load_feed_from_disk()
    if _feed_cache is None:
        await _refresh_feed()
    elif _feed_stale():
        await _refresh_feed()
    return _feed_cache or set()


async def check(domain_or_url: str) -> SignalResult:
    weights = _load_weights()
    try:
        feed = await asyncio.wait_for(get_feed(), timeout=20)
    except Exception:
        return SignalResult(
            signal_name="openphish",
            category="reputation",
            passed=True,
            deduction=0,
            detail="OpenPhish feed could not be loaded.",
            available=False,
            availability_reason="feed_unavailable",
        )

    if not feed:
        return SignalResult(
            signal_name="openphish",
            category="reputation",
            passed=True,
            deduction=0,
            detail="OpenPhish feed is empty — phishing feed check not usable.",
            available=False,
            availability_reason="feed_empty",
        )

    found = url_in_feed(domain_or_url, feed)
    if found:
        return SignalResult(
            signal_name="openphish",
            category="reputation",
            passed=False,
            deduction=weights.get("openphish_hit", 40),
            detail="URL was found in the OpenPhish active phishing feed.",
            raw_data={"feed_size": len(feed)},
        )

    return SignalResult(
        signal_name="openphish",
        category="reputation",
        passed=True,
        deduction=0,
        detail=f"Domain not found in OpenPhish feed ({len(feed)} entries cached).",
        raw_data={"feed_size": len(feed)},
    )