import os
import base64
import json
import httpx
import tldextract
from app.models import SignalResult
from app.scoring.engine import _load_weights

_BRANDS_CACHE: set[str] | None = None


def _load_top_brands() -> set[str]:
    global _BRANDS_CACHE
    if _BRANDS_CACHE is None:
        path = os.path.join(os.path.dirname(__file__), "../../data/top_brands.json")
        with open(path) as f:
            _BRANDS_CACHE = set(json.load(f))
    return _BRANDS_CACHE


def _is_top_brand(domain_or_url: str) -> bool:
    try:
        extracted = tldextract.extract(domain_or_url)
        registrable = f"{extracted.domain}.{extracted.suffix}" if extracted.suffix else ""
    except Exception:
        registrable = ""
    return registrable in _load_top_brands()


def assess_stats(malicious: int, suspicious: int, is_brand: bool) -> tuple[bool, int, str, dict]:
    """Pure decision logic for VirusTotal stats. Returns (passed, deduction, detail, raw)."""
    weights = _load_weights()
    total_flagged = malicious + suspicious
    stats = {"malicious": malicious, "suspicious": suspicious}

    if total_flagged == 0:
        return True, 0, "Clean on VirusTotal (no engines flagged the URL).", stats

    if total_flagged >= 3:
        return (
            False,
            weights.get("virustotal_3plus", 30),
            f"Flagged by {total_flagged} engines ({malicious} malicious, {suspicious} suspicious) on VirusTotal.",
            stats,
        )

    if is_brand:
        return (
            True,
            0,
            f"VirusTotal reported {total_flagged} engine flag(s), but on a well-known brand domain "
            "this is low-confidence and was not counted.",
            stats,
        )

    if malicious >= 1:
        return (
            False,
            weights.get("virustotal_1_2", 10),
            f"Flagged as malicious by {malicious} engine(s) on VirusTotal.",
            stats,
        )

    return (
        False,
        weights.get("virustotal_suspicious_only", 5),
        f"Flagged as suspicious by {suspicious} engine(s) on VirusTotal.",
        stats,
    )


async def check(domain_or_url: str) -> SignalResult:
    api_key = os.getenv("VIRUSTOTAL_API_KEY", "")
    if not api_key:
        return SignalResult(
            signal_name="virustotal",
            category="reputation",
            passed=True,
            deduction=0,
            detail="VirusTotal check skipped (no API key configured).",
            available=False,
            availability_reason="not_configured",
        )

    url_id = base64.urlsafe_b64encode(domain_or_url.encode()).decode().strip("=")
    headers = {"x-apikey": api_key}
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(f"https://www.virustotal.com/api/v3/urls/{url_id}", headers=headers)
            if resp.status_code == 404:
                submit = await client.post(
                    "https://www.virustotal.com/api/v3/urls",
                    headers=headers,
                    data={"url": domain_or_url},
                )
                if submit.status_code not in (200, 201):
                    raise ValueError(f"VirusTotal submission returned {submit.status_code}")
                submitted_id = submit.json().get("data", {}).get("id")
                if not submitted_id:
                    raise ValueError("VirusTotal submission did not return an analysis ID")
                resp = await client.get(
                    f"https://www.virustotal.com/api/v3/urls/{url_id}",
                    headers=headers,
                )
            if resp.status_code != 200:
                raise ValueError(f"VirusTotal returned {resp.status_code}")
            data = resp.json()
    except Exception:
        return SignalResult(
            signal_name="virustotal",
            category="reputation",
            passed=True,
            deduction=0,
            detail="VirusTotal check could not be completed.",
            available=False,
        )

    stats = data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
    malicious = stats.get("malicious", 0)
    suspicious = stats.get("suspicious", 0)

    passed, deduction, detail, raw = assess_stats(malicious, suspicious, _is_top_brand(domain_or_url))
    return SignalResult(
        signal_name="virustotal",
        category="reputation",
        passed=passed,
        deduction=deduction,
        detail=detail,
        raw_data={"stats": raw},
    )