from urllib.parse import urlparse, urlunparse
import tldextract


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
