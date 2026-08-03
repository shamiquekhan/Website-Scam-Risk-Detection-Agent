import asyncio
import socket
import httpx
import tldextract
from datetime import datetime, timezone
from app.models import SignalResult
from app.scoring.engine import _load_weights

RDAP_TIMEOUT = 5
WHOIS_FALLBACK_TIMEOUT = 5


def _parse_rdap_date(date_str: str) -> datetime:
    if date_str.endswith("Z"):
        date_str = date_str[:-1] + "+00:00"
    return datetime.fromisoformat(date_str)


async def check(domain_or_url: str) -> SignalResult:
    extracted = tldextract.extract(domain_or_url)
    domain = f"{extracted.domain}.{extracted.suffix}" if extracted.domain and extracted.suffix else domain_or_url.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
    weights = _load_weights()
    try:
        async with httpx.AsyncClient(timeout=RDAP_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(f"https://rdap.org/domain/{domain}")
            if resp.status_code != 200:
                raise ValueError(f"RDAP returned {resp.status_code}")
            data = resp.json()
    except Exception:
        try:
            whois_data = await asyncio.wait_for(
                asyncio.to_thread(_whois_fallback, domain),
                timeout=WHOIS_FALLBACK_TIMEOUT,
            )
            days_old, registrar = whois_data
            privacy_protected = _is_privacy_protected(registrar)
            return _score(domain, days_old, registrar, privacy_protected, weights)
        except Exception:
            return SignalResult(
                signal_name="whois_check",
                category="domain_trust",
                passed=True,
                deduction=0,
                detail="Could not verify domain registration age.",
                available=False,
            )

    events = data.get("events", [])
    registration_event = None
    for e in events:
        if e.get("eventAction") == "registration":
            registration_event = e
            break
    if not registration_event:
        return SignalResult(
            signal_name="whois_check",
            category="domain_trust",
            passed=True,
            deduction=0,
            detail="Could not determine domain registration date.",
            available=False,
        )

    creation = _parse_rdap_date(registration_event["eventDate"])
    days_old = (datetime.now(timezone.utc) - creation).days
    entities = data.get("entities", [])
    registrar = "Unknown"
    for ent in entities:
        vcard = ent.get("vcardArray", [[]])[1] if ent.get("vcardArray") else []
        for item in vcard:
            if item and len(item) > 3 and item[0] == "fn":
                registrar = item[3]
                break

    privacy_protected = _is_privacy_protected(registrar) or _has_redacted_entity(data)
    return _score(domain, days_old, registrar, privacy_protected, weights)


def _whois_fallback(domain: str) -> tuple[int, str]:
    import whois

    socket.setdefaulttimeout(WHOIS_FALLBACK_TIMEOUT)
    w = whois.whois(domain)
    creation_date = w.creation_date
    if isinstance(creation_date, list):
        creation_date = creation_date[0]
    if not creation_date:
        raise ValueError("No creation date in WHOIS")
    days_old = (datetime.now(timezone.utc) - creation_date).days
    registrar = w.registrar or "Unknown"
    return days_old, registrar


def _is_privacy_protected(value: str) -> bool:
    lowered = value.lower()
    return any(term in lowered for term in ("privacy", "redacted", "protected", "whoisguard", "proxy"))


def _has_redacted_entity(data: dict) -> bool:
    serialized = str(data.get("entities", [])).lower()
    return any(term in serialized for term in ("redacted", "privacy", "protected"))


def _score(domain: str, days_old: int, registrar: str, privacy_protected: bool, weights: dict) -> SignalResult:
    if days_old < 30:
        deduction = weights.get("domain_age_under_30", 25)
        detail = f"Domain registered {days_old} days ago — very new domains are frequently used for short-lived scam campaigns."
    elif days_old < 180:
        deduction = weights.get("domain_age_30_to_180", 12)
        detail = f"Domain registered {days_old} days ago — moderately new."
    else:
        deduction = 0
        detail = f"Domain is {days_old} days old — established domain."

    passed = deduction == 0

    return SignalResult(
        signal_name="whois_check",
        category="domain_trust",
        passed=passed,
        deduction=deduction if not passed else 0,
        detail=detail,
        raw_data={
            "days_old": days_old,
            "registrar": registrar,
            "privacy_protected": privacy_protected,
        },
    )
