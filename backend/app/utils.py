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
