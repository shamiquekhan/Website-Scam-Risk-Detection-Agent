import asyncio
import socket
import time
import httpx
import tldextract
from datetime import datetime, timezone
from app.models import SignalResult
from app.scoring.engine import _load_weights

RDAP_TIMEOUT = 4
WHOIS_FALLBACK_TIMEOUT = 3
BOOTSTRAP_URL = "https://data.iana.org/rdap/dns.json"
BOOTSTRAP_TTL = 24 * 3600

_bootstrap: dict | None = None
_bootstrap_fetched_at: float = 0.0


async def _get_bootstrap() -> dict | None:
    global _bootstrap, _bootstrap_fetched_at
    if _bootstrap is not None and (time.time() - _bootstrap_fetched_at) < BOOTSTRAP_TTL:
        return _bootstrap
    try:
        async with httpx.AsyncClient(timeout=RDAP_TIMEOUT) as client:
            resp = await client.get(BOOTSTRAP_URL)
        if resp.status_code == 200:
            _bootstrap = resp.json()
            _bootstrap_fetched_at = time.time()
    except Exception:
        pass
    return _bootstrap


def _authoritative_rdap_urls(bootstrap: dict | None, suffix: str) -> list[str]:
    if not bootstrap:
        return []
    label = f".{suffix.lower()}"
    for entry in bootstrap.get("services", []):
        if len(entry) >= 2 and entry[0] and label in entry[0]:
            return entry[1]
    return []


def _parse_rdap_date(date_str: str) -> datetime:
    if date_str.endswith("Z"):
        date_str = date_str[:-1] + "+00:00"
    return datetime.fromisoformat(date_str)


async def check(domain_or_url: str) -> SignalResult:
    extracted = tldextract.extract(domain_or_url)
    domain = f"{extracted.domain}.{extracted.suffix}" if extracted.domain and extracted.suffix else domain_or_url.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
    weights = _load_weights()

    candidates = list(_authoritative_rdap_urls(await _get_bootstrap(), extracted.suffix))
    if not candidates:
        candidates = [f"https://rdap.org/domain/{domain}"]
    candidates = [base.rstrip("/") + "/domain/" + domain for base in candidates]

    data = None
    for url in candidates:
        try:
            async with httpx.AsyncClient(timeout=RDAP_TIMEOUT, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    break
        except Exception:
            continue

    if data is None:
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

    try:
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
            vcard_array = ent.get("vcardArray") or [[]]
            vcard = vcard_array[1] if len(vcard_array) > 1 else []
            for item in vcard:
                if item and len(item) > 3 and item[0] == "fn":
                    registrar = item[3]
                    break

        privacy_protected = _is_privacy_protected(registrar) or _has_redacted_entity(data)
        return _score(domain, days_old, registrar, privacy_protected, weights)
    except Exception:
        return SignalResult(
            signal_name="whois_check",
            category="domain_trust",
            passed=True,
            deduction=0,
            detail="Could not parse domain registration data.",
            available=False,
        )


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
    elif days_old < 90:
        deduction = weights.get("domain_age_30_to_90", 15)
        detail = f"Domain registered {days_old} days ago — recent registrations are more often tied to short-lived scam campaigns."
    elif days_old < 180:
        deduction = weights.get("domain_age_90_to_180", 12)
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
