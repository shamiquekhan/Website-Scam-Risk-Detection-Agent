from urllib.parse import urlparse, urlunparse
import tldextract

try:
    from rapidfuzz.distance import Levenshtein as _Levenshtein
except Exception:  # pragma: no cover - fallback when C extension is unavailable
    _Levenshtein = None


def levenshtein_distance(a: str, b: str) -> int:
    """Edit distance via RapidFuzz, falling back to a pure-Python DP when the
    C extension cannot be installed (e.g. build failures on new Python versions)."""
    if _Levenshtein is not None:
        return _Levenshtein.distance(a, b)
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    prev = list(range(lb + 1))
    for i, ca in enumerate(a, 1):
        curr = [i] + [0] * lb
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[lb]


def normalize_url(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        raise ValueError("URL is empty")
    parsed = urlparse(raw)
    if not parsed.scheme:
        raw = "https://" + raw
        parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")
    hostname = parsed.hostname.lower() if parsed.hostname else ""
    if not hostname:
        raise ValueError("URL has no hostname")
    path = parsed.path or "/"
    query = parsed.query or ""
    normalized = urlunparse((parsed.scheme, hostname, path, parsed.params, query, parsed.fragment))
    return normalized


def extract_domain(url: str) -> str:
    extracted = tldextract.extract(url)
    domain = extracted.registered_domain
    if not domain:
        raise ValueError(f"Could not extract domain from: {url}")
    return domain.lower()


def _normalize_entry(url: str) -> str:
    """Return a comparable 'host/path' key for a feed entry, lowercased."""
    url = url.strip()
    parsed = urlparse(url if url.startswith("http") else "https://" + url)
    host = (parsed.hostname or "").lower()
    path = parsed.path or "/"
    if path.endswith("/") and path != "/":
        path = path[:-1]
    return f"{host}{path}"


def url_in_feed(url: str, entries: set[str]) -> bool:
    """Path-aware check: matches root-level flags and exact/deeper paths,
    but does NOT taint a domain when the reported URL has a deeper path
    and the scanned URL is the bare host/root."""
    scanned = _normalize_entry(url)
    if scanned in entries:
        return True

    scanned_host, sep, scanned_path = scanned.partition("/")
    scanned_path = scanned_path or ""
    for entry in entries:
        host, _, path = entry.partition("/")
        if host != scanned_host:
            continue
        if not path and not scanned_path:
            return True
        if not path:
            return True
        if not scanned_path:
            continue
        if scanned_path.startswith(path):
            return True
    return False
