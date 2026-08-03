import os
import base64
import httpx
from app.models import SignalResult
from app.scoring.engine import _load_weights


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
    total_flagged = malicious + suspicious

    weights = _load_weights()
    if total_flagged >= 3:
        return SignalResult(
            signal_name="virustotal",
            category="reputation",
            passed=False,
            deduction=weights.get("virustotal_3plus", 30),
            detail=f"Flagged by {total_flagged} engines ({malicious} malicious, {suspicious} suspicious) on VirusTotal.",
            raw_data={"stats": stats},
        )
    if total_flagged >= 1:
        return SignalResult(
            signal_name="virustotal",
            category="reputation",
            passed=False,
            deduction=weights.get("virustotal_1_2", 10),
            detail=f"Flagged by {total_flagged} engine(s) on VirusTotal.",
            raw_data={"stats": stats},
        )

    return SignalResult(
        signal_name="virustotal",
        category="reputation",
        passed=True,
        deduction=0,
        detail=f"Clean on VirusTotal ({stats.get('harmless', 0)} engines checked, none flagged).",
    )
