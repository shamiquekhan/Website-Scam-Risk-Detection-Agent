# Architecture

## Overview

```
                         ┌─────────────────────────┐
                         │  Frontend (Next.js +     │
                         │  Tailwind, dark mode)    │
                         └────────────┬─────────────┘
                                      │ POST /scan {url}  |  POST /scan/batch
                                      ▼
                         ┌─────────────────────────┐
                         │   FastAPI Backend        │
                         │   /scan /scan/batch      │
                         └────────────┬─────────────┘
                                      │
                     ┌────────────────┼─────────────────────┐
                     ▼                ▼                      ▼
           ┌─────────────────┐ ┌──────────────┐   ┌───────────────────┐
           │ Orchestrator     │ │ Cache layer  │   │ Rate limiter       │
           │ (asyncio.gather, │ │ (SQLite,     │   │ (slowapi, per IP)  │
           │  8s per check)   │ │  24h TTL)    │   │                    │
           └────────┬─────────┘ └──────────────┘   └───────────────────┘
                    │ fan-out to signal collectors (parallel, async)
     ┌──────────────┼───────────────┬───────────────────┬────────────────┐
     ▼              ▼               ▼                   ▼                ▼
┌────────┐   ┌────────────┐  ┌──────────────┐   ┌──────────────┐  ┌─────────────┐
│ WHOIS/ │   │ SSL/TLS    │  │ DNS/Hosting  │   │ URLhaus      │  │ OpenPhish   │
│ RDAP   │   │ Certificate│  │ (ASN, geo)   │   │ blocklist    │  │ feed (6h)   │
│ Age    │   │            │  │              │   │ (keyless)    │  │ (keyless)   │
└────┬────┘   └─────┬──────┘  └──────┬───────┘   └──────┬───────┘  └──────┬──────┘
     └──────────────┴──────┬────────┴──────────────────┴─────────────────┘
                           ▼
              ┌───────────────────────────┐
              │  LOCAL ML (ONNX Runtime)   │
              │  phishing classifier       │
              │  URL lexical features      │
              └─────────────┬─────────────┘
                            │
              ┌─────────────┴─────────────┐
              │  Scoring Engine (weights   │
              │  v2, deterministic,        │
              │  blacklist hard-cap,       │
              │  completeness factor)      │
              └─────────────┬─────────────┘
                            ▼
              ┌───────────────────────────┐
              │  LLM Summarizer           │
              │  Ollama (local) → Groq →  │
              │  templated fallback       │
              └─────────────┬─────────────┘
                            ▼
              Response: score, verdict, signals[], confidence, summary
```

## Signal collectors (11)

| Collector | File | Data source | Always available? |
|-----------|------|-------------|-------------------|
| SSL/TLS | `collectors/ssl_check.py` | Direct socket | No (needs a reachable site) |
| Domain age | `collectors/whois_check.py` | IANA RDAP bootstrap → `rdap.org` → `python-whois` | No |
| DNS + hosting | `collectors/dns_hosting.py` | `dns.resolver`, `ip-api.com`, `ipwho.is` | No |
| Google Safe Browsing | `collectors/safe_browsing.py` | Google API (optional key) | No (skipped without key) |
| VirusTotal | `collectors/virustotal.py` | VirusTotal API (optional key) | No (skipped without key) |
| URLhaus | `collectors/urlhaus.py` | Keyless blocklist, or auth API with key | Yes when feed cached |
| OpenPhish | `collectors/openphish.py` | Keyless feed, refreshed every 6h | Yes when feed cached |
| Local ML | `collectors/local_ml.py` | ONNX model via `ml/inference.py` | Yes when model bundled |
| URL structure | `collectors/domain_lexical.py` | Deterministic rules | Yes |
| Content heuristics | `collectors/content_heuristics.py` | Page fetch + `BeautifulSoup` | No (needs reachable site) |
| Typosquat | `collectors/typosquat.py` | `top_brands.json` + Levenshtein | Yes |

The `openphish` and `urlhaus` signals use **path-aware feed matching**
(`app/utils.py:url_in_feed`): a reported URL like `github.com/user/repo/releases/...`
does **not** taint the bare `github.com` domain, while a domain-root report (e.g.
`evil.tk/`) flags the whole domain.

## Scoring (weights v2)

- Start at 100; subtract per-signal deductions from `scoring/weights.json`.
- **Blacklist hard-cap**: any hit on OpenPhish, URLhaus, or Safe Browsing caps the
  score at 29 (High Risk) regardless of other signals.
- **Completeness factor**: final score is scaled by `completed / total`; fewer than
  6 of 11 completed checks yields **Insufficient Data** (fail-closed).
- Verdict bands: **90-100 Safe**, **70-89 Likely Safe**, **50-69 Caution**,
  **30-49 Suspicious**, **0-29 High Risk**.

## ML model

- Trained with `ml_training/` on OpenPhish positives + synthetic phishing variants
  and Majestic Million negatives.
- Random Forest exported to ONNX (`models/phishing_classifier.onnx`), run with
  ONNX Runtime - no API call, no rate limit.
- 12 lexical features (length, dots, subdomain depth, digit/special ratios,
  entropy, `@`-sign, IP literal, HTTPS, hyphens, risky TLD, brand distance).
- Degrades to `available: false` if the model file is missing.

## Cache, rate limiting, batch

- **SQLite** cache keyed by normalized domain, 24h TTL; insufficient scans are not cached.
- **slowapi** rate limits `/scan` (10/min) and `/scan/batch` (5/min) per IP.
- **`/scan/batch`** accepts up to 100 URLs, scans with a configurable concurrency cap
  (default 4), and returns per-URL results plus any failures.