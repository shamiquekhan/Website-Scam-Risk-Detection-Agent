"""Feature engineering + dataset assembly for the phishing classifier.

Combines real OpenPhish positives with realistic synthetic phishing variants,
and clean legit domains (with legit subdomains) as negatives.
"""

import random
from pathlib import Path

from app.ml.feature_extractor import extract_features

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "training"
PHISHING_FILE = DATA_DIR / "phishing_urls.txt"
LEGIT_FILE = DATA_DIR / "legit_domains.txt"

SUSPICIOUS_TLDS = ["tk", "ml", "cf", "ga", "gq", "xyz", "top", "icu", "buzz", "click", "loan", "work", "country", "stream", "gdn", "men", "review", "download", "racing", "win", "party", "date", "online", "site", "website", "space", "club", "cam", "cyou", "quest"]
SECURE_PREFIXES = ["secure", "login", "account", "verify", "update", "signin", "webmail", "support", "billing"]
HOMOGLYPHS = {"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "6": "g", "7": "t", "8": "b", "9": "g"}


def _read_phishing() -> list[str]:
    if not PHISHING_FILE.exists():
        return []
    return [line.strip() for line in PHISHING_FILE.open() if line.strip()]


def _read_legit() -> list[str]:
    if not LEGIT_FILE.exists():
        return []
    return [line.strip() for line in LEGIT_FILE.open() if line.strip()]


def _typosquat(domain: str) -> str:
    root = domain.split(".")[0]
    if len(root) < 3:
        return root + "x." + ".".join(domain.split(".")[1:])
    pos = random.randrange(len(root))
    letter = root[pos]
    if letter.isdigit() and letter in HOMOGLYPHS:
        replacement = HOMOGLYPHS[letter]
    else:
        replacement = random.choice("abcdefghijklmnopqrstuvwxyz")
        if replacement == letter:
            replacement = "x"
    mutated = root[:pos] + replacement + root[pos + 1 :]
    return mutated + "." + ".".join(domain.split(".")[1:])


def _suspicious_tld_variant(domain: str) -> str:
    parts = domain.split(".")
    root = parts[0]
    tld = random.choice(SUSPICIOUS_TLDS)
    return f"{root}.{tld}"


def _subdomain_variant(domain: str) -> str:
    return f"{random.choice(SECURE_PREFIXES)}-{random.randrange(1000, 99999)}.{domain}"


def _hyphen_variant(domain: str) -> str:
    root = domain.split(".")[0]
    return f"{root}-{random.choice(SECURE_PREFIXES)}.{random.choice(SUSPICIOUS_TLDS)}"


def _entropy_variant(domain: str) -> str:
    chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    token = "".join(random.choice(chars) for _ in range(random.randint(12, 20)))
    return f"{token}.{random.choice(SUSPICIOUS_TLDS)}"


def _double_sub_variant(domain: str) -> str:
    root = domain.split(".")[0]
    return f"{random.choice(SECURE_PREFIXES)}.{root}-{random.choice(SECURE_PREFIXES)}.{domain.split('.')[-1]}"


def _generate_phishing_variants(legit: list[str], count: int) -> list[str]:
    variants = []
    generators = [_typosquat, _suspicious_tld_variant, _subdomain_variant, _hyphen_variant, _entropy_variant, _double_sub_variant]
    while len(variants) < count:
        domain = random.choice(legit)
        generator = random.choice(generators)
        variants.append("https://" + generator(domain) + "/")
    return variants


def build_dataset(max_per_class: int = 8000, seed: int = 42, augment_ratio: int = 6) -> tuple[list[str], list[int]]:
    random.seed(seed)
    phishing = _read_phishing()
    legit = _read_legit()

    if not phishing or not legit:
        raise RuntimeError(
            "Training data missing. Run `python -m ml_training.fetch_data` first."
        )

    phishing_urls = ["https://" + u if not u.startswith("http") else u for u in phishing]

    synthetic = _generate_phishing_variants(legit, len(phishing_urls) * augment_ratio)
    all_positive = phishing_urls + synthetic
    if len(all_positive) > max_per_class:
        all_positive = random.sample(all_positive, max_per_class)

    legit_domains = [d for d in legit if "." in d and len(d) < 40]
    legit_urls = ["https://" + d + "/" for d in legit_domains]
    legit_subdomains = [
        f"https://{random.choice(SECURE_PREFIXES)}.{d}/" for d in random.sample(legit_domains, min(len(legit_domains), max_per_class // 2))
    ]
    legit_hyphens = [
        f"https://{d.split('.')[0]}-{random.choice(SECURE_PREFIXES)}.{d.split('.')[-1]}/"
        for d in random.sample(legit_domains, min(len(legit_domains), max_per_class // 3))
    ]
    all_negative = legit_urls + legit_subdomains + legit_hyphens
    if len(all_negative) > max_per_class:
        all_negative = random.sample(all_negative, max_per_class)

    urls = all_positive + all_negative
    labels = [1] * len(all_positive) + [0] * len(all_negative)
    return urls, labels


def build_feature_matrix(urls: list[str]):
    import numpy as np

    X = np.array([extract_features(u) for u in urls], dtype=np.float32)
    return X