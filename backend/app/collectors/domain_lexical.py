import math
import re
from urllib.parse import urlparse

from app.ml.feature_extractor import SUSPICIOUS_TLDS
from app.models import SignalResult
from app.scoring.engine import _load_weights

HIGH_ENTROPY_THRESHOLD = 3.6


def _shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    counts = {}
    for ch in text:
        counts[ch] = counts.get(ch, 0) + 1
    length = len(text)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


async def check(domain_or_url: str) -> SignalResult:
    parsed = urlparse(domain_or_url if domain_or_url.startswith("http") else "https://" + domain_or_url)
    host = parsed.hostname or ""
    host = host.lower().replace("www.", "")

    weights = _load_weights()
    deduction = 0
    details = []

    parts = [p for p in host.split(".") if p]
    tld = parts[-1] if parts else ""

    if tld in SUSPICIOUS_TLDS:
        deduction += weights.get("suspicious_tld", 10)
        details.append(f"Top-level domain .{tld} is frequently abused for throwaway scam sites.")

    if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host) and ":" not in host:
        entropy = _shannon_entropy(host)
        if entropy > HIGH_ENTROPY_THRESHOLD:
            deduction += weights.get("high_entropy_host", 5)
            details.append("The domain looks randomly generated (high character entropy) - common for automated phishing.")

    if len(host) > 30 and host.count(".") >= 3:
        deduction += weights.get("long_subdomain_chain", 5)
        details.append("Unusually long, multi-part domain name - often used to hide the real site name.")

    if "@" in (parsed.netloc or ""):
        deduction += weights.get("at_sign_in_url", 15)
        details.append("URL contains an '@' in the host portion - a classic phishing trick to disguise the real destination.")

    if not details:
        details.append("No suspicious URL structure detected.")

    return SignalResult(
        signal_name="domain_lexical",
        category="domain_trust",
        passed=deduction == 0,
        deduction=deduction,
        detail=" ".join(details),
        raw_data={"host": host, "tld": tld},
    )