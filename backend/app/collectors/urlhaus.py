import os
import httpx
from app.models import SignalResult
from app.scoring.engine import _load_weights

URLHAUS_LOOKUP_URL = "https://urlhaus-api.abuse.ch/v1/url/"


async def check(domain_or_url: str) -> SignalResult:
    auth_key = os.getenv("URLHAUS_AUTH_KEY", "")
    if not auth_key:
        return SignalResult(
            signal_name="urlhaus",
            category="reputation",
            passed=True,
            deduction=0,
            detail="URLhaus check skipped (no API key configured).",
            available=False,
            availability_reason="not_configured",
        )

    headers = {"Auth-Key": auth_key}
    payload = {"url": domain_or_url}
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.post(URLHAUS_LOOKUP_URL, headers=headers, data=payload)
            if resp.status_code == 409:
                weights = _load_weights()
                return SignalResult(
                    signal_name="urlhaus",
                    category="reputation",
                    passed=False,
                    deduction=weights.get("urlhaus_hit", 35),
                    detail="URL flagged in the URLhaus malware/phishing database.",
                    raw_data={"urlhaus_response": resp.json()},
                )
            if resp.status_code == 404:
                return SignalResult(
                    signal_name="urlhaus",
                    category="reputation",
                    passed=True,
                    deduction=0,
                    detail="URL not found in the URLhaus malware/phishing database.",
                )
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
        return SignalResult(
            signal_name="urlhaus",
            category="reputation",
            passed=True,
            deduction=0,
            detail="URL not found in the URLhaus malware/phishing database.",
        )

    if result.get("blacklist_status") == "not_blacklisted" and result.get("url_status") in ("online", "offline"):
        return SignalResult(
            signal_name="urlhaus",
            category="reputation",
            passed=True,
            deduction=0,
            detail="URL not blacklisted in URLhaus.",
            raw_data={"query_status": result.get("query_status")},
        )

    weights = _load_weights()
    return SignalResult(
        signal_name="urlhaus",
        category="reputation",
        passed=False,
        deduction=weights.get("urlhaus_hit", 35),
        detail="URL flagged in the URLhaus malware/phishing database.",
        raw_data={"query_status": result.get("query_status"), "blacklist_status": result.get("blacklist_status")},
    )
