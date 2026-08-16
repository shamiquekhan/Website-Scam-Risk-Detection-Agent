"""Download free training data: OpenPhish (phishing positives) + Majestic Million (legit negatives).

Sources (all free, no API keys):
- https://openphish.com/feed.txt            active phishing URLs, refreshed every 6h
- https://downloads.majestic.com/majestic_million.csv   top ~1M legit domains
"""

import os
from pathlib import Path

import httpx

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "training"
PHISHING_FILE = DATA_DIR / "phishing_urls.txt"
LEGIT_FILE = DATA_DIR / "legit_domains.txt"

OPENPHISH_URL = "https://openphish.com/feed.txt"
MAJESTIC_URL = "https://downloads.majestic.com/majestic_million.csv"
LEGIT_LIMIT = 100_000


def ensure_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def download_openphish() -> int:
    ensure_dir()
    if PHISHING_FILE.exists() and PHISHING_FILE.stat().st_size > 0:
        print(f"OpenPhish feed already cached ({PHISHING_FILE.stat().st_size} bytes).")
        return sum(1 for _ in PHISHING_FILE.open())
    resp = httpx.get(OPENPHISH_URL, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    PHISHING_FILE.write_bytes(resp.content)
    count = sum(1 for _ in PHISHING_FILE.open())
    print(f"Downloaded {count} phishing URLs from OpenPhish.")
    return count


def download_majestic() -> int:
    ensure_dir()
    if LEGIT_FILE.exists() and LEGIT_FILE.stat().st_size > 0:
        print(f"Majestic list already cached ({LEGIT_FILE.stat().st_size} bytes).")
        return sum(1 for _ in LEGIT_FILE.open())
    count = 0
    with LEGIT_FILE.open("w") as out:
        with httpx.stream("GET", MAJESTIC_URL, timeout=120, follow_redirects=True) as resp:
            resp.raise_for_status()
            for line_number, line in enumerate(resp.iter_lines()):
                if line_number == 0 or not line:
                    continue
                domain = line.split(",")[2]
                if domain:
                    out.write(domain + "\n")
                    count += 1
                if count >= LEGIT_LIMIT:
                    break
    print(f"Downloaded {count} legit domains from Majestic Million.")
    return count


def download_all() -> None:
    download_openphish()
    download_majestic()


if __name__ == "__main__":
    download_all()