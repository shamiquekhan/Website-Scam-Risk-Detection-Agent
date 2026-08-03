import os
import httpx
from app.models import SignalResult
from app.scoring.engine import _load_weights


async def check(domain_or_url: str) -> SignalResult:
    api_key = os.getenv("GOOGLE_SAFE_BROWSING_API_KEY", "")
    if not api_key:
        return SignalResult(
            signal_name="safe_browsing",
            category="reputation",
            passed=True,
            deduction=0,
            detail="Google Safe Browsing check skipped (no API key configured).",
            available=False,
            availability_reason="not_configured",
        )

    url = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={api_key}"
    body = {
        "client": {"clientId": "website-scam-detector", "clientVersion": "1.0.0"},
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": domain_or_url}],
        },
    }
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.post(url, json=body)
            if resp.status_code != 200:
                raise ValueError(f"Safe Browsing returned {resp.status_code}")
            data = resp.json()
    except Exception:
        return SignalResult(
            signal_name="safe_browsing",
            category="reputation",
            passed=True,
            deduction=0,
            detail="Google Safe Browsing check could not be completed.",
            available=False,
        )

    matches = data.get("matches", [])
    if matches:
        threat_types = [m["threatType"] for m in matches]
        weights = _load_weights()
        return SignalResult(
            signal_name="safe_browsing",
            category="reputation",
            passed=False,
            deduction=weights.get("safe_browsing_hit", 40),
            detail=f"Flagged by Google Safe Browsing: {', '.join(threat_types)}.",
            raw_data={"matches": matches},
        )

    return SignalResult(
        signal_name="safe_browsing",
        category="reputation",
        passed=True,
        deduction=0,
        detail="No threats found by Google Safe Browsing.",
    )
