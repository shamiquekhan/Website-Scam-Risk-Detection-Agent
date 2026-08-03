import json
import os
import Levenshtein
from app.models import SignalResult
from app.scoring.engine import _load_weights

HOMOGLYPHS = {
    "0": "o", "1": "l", "3": "e", "4": "a", "5": "s",
    "6": "g", "7": "t", "8": "b", "9": "g",
}


def _load_brands() -> list[str]:
    path = os.path.join(os.path.dirname(__file__), "../../data/top_brands.json")
    with open(path) as f:
        return json.load(f)


def _normalize_for_typosquat(domain: str) -> str:
    domain = domain.lower().replace("www.", "")
    normalized = []
    for ch in domain:
        if ch in HOMOGLYPHS:
            normalized.append(HOMOGLYPHS[ch])
        else:
            normalized.append(ch)
    return "".join(normalized)


async def check(domain_or_url: str) -> SignalResult:
    domain = domain_or_url.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
    domain = domain.lower().replace("www.", "")
    brands = _load_brands()
    weights = _load_weights()
    normalized_domain = _normalize_for_typosquat(domain)

    for brand in brands:
        brand_clean = brand.lower().replace("www.", "")
        if domain == brand_clean:
            continue

        distance = Levenshtein.distance(normalized_domain, brand_clean)
        if distance <= 2:
            return SignalResult(
                signal_name="typosquat",
                category="brand",
                passed=False,
                deduction=weights.get("typosquat", 30),
                detail=f"Domain closely resembles '{brand}' (typosquat distance: {distance}) — possible impersonation.",
                raw_data={"resembles": brand, "distance": distance},
            )

    return SignalResult(
        signal_name="typosquat",
        category="brand",
        passed=True,
        deduction=0,
        detail="No typosquatting or brand impersonation detected.",
    )
