import warnings
import httpx
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from urllib.parse import urlparse
from app.models import SignalResult
from app.scoring.engine import _load_weights

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

URGENCY_KEYWORDS = [
    "verify your account", "act now", "suspended", "confirm immediately",
    "unusual activity", "account will be closed", "update your payment",
    "security alert", "limited time", "urgent action required",
]


async def check(domain_or_url: str) -> SignalResult:
    weights = _load_weights()
    url = domain_or_url
    if not url.startswith("http"):
        url = "https://" + url

    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True, max_redirects=5) as client:
            resp = await client.get(url)
    except Exception:
        return SignalResult(
            signal_name="content_heuristics",
            category="content",
            passed=True,
            deduction=0,
            detail="Could not fetch page content for analysis.",
            available=False,
        )

    deduction = 0
    details = []
    final_url = str(resp.url)
    original_domain = urlparse(domain_or_url if domain_or_url.startswith("http") else "https://" + domain_or_url).hostname or ""
    final_domain = urlparse(final_url).hostname or ""

    if final_domain and original_domain and final_domain != original_domain:
        deduction += weights.get("excessive_redirects", 12)
        details.append(f"Final destination ({final_domain}) differs from entered domain.")

    try:
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception:
        return SignalResult(
            signal_name="content_heuristics",
            category="content",
            passed=deduction == 0,
            deduction=deduction,
            detail=" ".join(details) if details else "Page content could not be parsed.",
            available=True,
        )

    forms = soup.find_all("form")
    has_password_form = False
    for form in forms:
        inputs = form.find_all("input", {"type": "password"})
        if inputs:
            has_password_form = True
            break

    if has_password_form and not final_url.startswith("https://"):
        deduction += weights.get("password_form_no_https", 20)
        details.append("Password form detected on a non-HTTPS page - credentials would be sent unencrypted.")

    page_text = soup.get_text(separator=" ", strip=True).lower()
    has_urgency = any(kw in page_text for kw in URGENCY_KEYWORDS)
    if has_urgency and has_password_form:
        deduction += weights.get("urgency_language_with_form", 10)
        details.append("Urgency/pressure language detected alongside a form - common in phishing pages.")

    if not details:
        details.append("No suspicious content patterns detected.")

    return SignalResult(
        signal_name="content_heuristics",
        category="content",
        passed=deduction == 0,
        deduction=deduction,
        detail=" ".join(details),
        raw_data={"final_url": final_url, "has_password_form": has_password_form, "has_urgency": has_urgency},
    )
