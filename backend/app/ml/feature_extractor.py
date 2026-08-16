import json
import math
import os
import re
from urllib.parse import urlparse

import Levenshtein

FEATURE_COUNT = 12

SUSPICIOUS_TLDS = {
    "tk", "ml", "cf", "ga", "gq", "xyz", "top", "icu", "buzz", "click",
    "loan", "work", "country", "stream", "gdn", "men", "review", "download",
    "racing", "win", "party", "date", "online", "site", "website", "space",
    "club", "cam", "cyou", "quest", "rest", "run", "store", "pro", "link",
}

_BRANDS_CACHE: set[str] | None = None


def _load_brands() -> set[str]:
    global _BRANDS_CACHE
    if _BRANDS_CACHE is None:
        path = os.path.join(os.path.dirname(__file__), "../../data/top_brands.json")
        with open(path) as f:
            _BRANDS_CACHE = set(json.load(f))
    return _BRANDS_CACHE


def _shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    counts = {}
    for ch in text:
        counts[ch] = counts.get(ch, 0) + 1
    length = len(text)
    entropy = -sum((count / length) * math.log2(count / length) for count in counts.values())
    return entropy


def _min_brand_distance(host: str) -> float:
    best = 1.0
    for brand in _load_brands():
        b = brand.lower().replace("www.", "")
        if host == b:
            best = 0.0
            break
        distance = Levenshtein.distance(host, b) / max(len(host), len(b), 1)
        best = min(best, distance)
    return best


def extract_features(url: str) -> list[float]:
    parsed = urlparse(url if url.startswith("http") else "https://" + url)
    host = parsed.hostname or ""
    host = host.lower().replace("www.", "")
    full = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    is_ip = bool(re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host)) or ("[" in host and "]" in host)
    if is_ip:
        subdomains = 0
        tld = ""
    else:
        parts = [p for p in host.split(".") if p]
        subdomains = max(len(parts) - 2, 0)
        tld = parts[-1] if parts else ""

    special = [ch for ch in full if not ch.isalnum()]
    digits = [ch for ch in full if ch.isdigit()]

    features = [
        min(len(full) / 200.0, 1.0),
        min(full.count(".") / 10.0, 1.0),
        min(subdomains / 4.0, 1.0),
        len(digits) / max(len(full), 1),
        len(special) / max(len(full), 1),
        _shannon_entropy(host) / 6.0,
        1.0 if "@" in full else 0.0,
        1.0 if is_ip else 0.0,
        1.0 if parsed.scheme == "https" else 0.0,
        1.0 if "-" in host else 0.0,
        1.0 if tld in SUSPICIOUS_TLDS else 0.0,
        _min_brand_distance(host),
    ]
    return features