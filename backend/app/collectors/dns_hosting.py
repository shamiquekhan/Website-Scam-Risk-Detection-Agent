import asyncio
import json
import os
import dns.resolver
import httpx
from app.models import SignalResult
from app.scoring.engine import _load_weights

DNS_TIMEOUT = 3
HTTP_TIMEOUT = 4


async def check(domain_or_url: str) -> SignalResult:
    domain = domain_or_url.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
    weights = _load_weights()
    asn_path = os.path.join(os.path.dirname(__file__), "../../data/high_risk_asn.json")
    with open(asn_path) as f:
        high_risk_asns = set(json.load(f))

    try:
        answers = await asyncio.wait_for(
            asyncio.to_thread(dns.resolver.resolve, domain, "A"),
            timeout=DNS_TIMEOUT,
        )
        ip = str(answers[0])
    except asyncio.TimeoutError:
        return SignalResult(
            signal_name="dns_hosting",
            category="hosting",
            passed=False,
            deduction=weights.get("dns_resolution_failure", 25),
            detail="Domain name resolution timed out — the site could not be verified or reached.",
            available=True,
            availability_reason="dns_failure",
        )
    except Exception:
        return SignalResult(
            signal_name="dns_hosting",
            category="hosting",
            passed=False,
            deduction=weights.get("dns_resolution_failure", 25),
            detail="Domain did not resolve to an IP address — the site could not be verified or reached.",
            available=True,
            availability_reason="dns_failure",
        )

    loc = await _get_hosting_info(ip)
    if loc is None:
        return SignalResult(
            signal_name="dns_hosting",
            category="hosting",
            passed=True,
            deduction=0,
            detail="Could not retrieve hosting information.",
            available=False,
        )
    asn, org, country = loc

    passed = True
    deduction = 0
    details = []

    if asn in high_risk_asns:
        deduction += weights.get("high_risk_asn", 10)
        details.append(f"Hosted on ASN {asn} — associated with high-abuse hosting.")

    country_by_tld = {
        "au": "AU", "br": "BR", "ca": "CA", "de": "DE", "fr": "FR",
        "in": "IN", "it": "IT", "jp": "JP", "mx": "MX", "nl": "NL",
        "nz": "NZ", "sg": "SG", "za": "ZA", "uk": "GB",
    }
    tld = domain.rsplit(".", 1)[-1].lower()
    expected_country = country_by_tld.get(tld)
    if expected_country and country != "Unknown" and country != expected_country:
        deduction += weights.get("hosting_country_mismatch", 8)
        details.append(
            f"Hosting country ({country}) differs from the domain country ({expected_country})."
        )

    if not details:
        details.append(f"Hosting: {org} ({country}).")

    return SignalResult(
        signal_name="dns_hosting",
        category="hosting",
        passed=deduction == 0,
        deduction=deduction,
        detail=" ".join(details),
        raw_data={"ip": ip, "asn": asn, "org": org, "country": country},
    )


async def _get_hosting_info(ip: str) -> tuple[str, str, str] | None:
    ipinfo_token = os.getenv("IPINFO_TOKEN", "")
    if ipinfo_token:
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                resp = await client.get(f"https://ipinfo.io/{ip}?token={ipinfo_token}")
                if resp.status_code == 200:
                    data = resp.json()
                    org = data.get("org", "Unknown")
                    return org.split()[0] if org else "", org, data.get("country", "Unknown")
        except Exception:
            pass

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.get(f"http://ip-api.com/json/{ip}")
            if resp.status_code != 200:
                return None
            data = resp.json()
            if data.get("status") != "success":
                return None
            asn = data.get("as", "")
            asn_number = asn.split()[0] if asn else ""
            org = data.get("isp", "") or data.get("org", "") or "Unknown"
            return asn_number, org, data.get("countryCode", "Unknown")
    except Exception:
        pass

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.get(f"https://ipwho.is/{ip}")
            if resp.status_code != 200:
                return None
            data = resp.json()
            if not data.get("success"):
                return None
            connection = data.get("connection", {}) or {}
            asn_number = str(connection.get("asn", "") or "")
            org = connection.get("org", "") or connection.get("isp", "") or "Unknown"
            return asn_number, org, data.get("country_code", "Unknown")
    except Exception:
        return None
