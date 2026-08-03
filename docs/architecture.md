# Architecture

## Overview

```
                         ┌─────────────────────────┐
                         │   Frontend (Next.js/     │
                         │   React + Tailwind)      │
                         └────────────┬─────────────┘
                                      │ POST /scan {url}
                                      ▼
                         ┌─────────────────────────┐
                         │   FastAPI Backend        │
                         │   /scan endpoint         │
                         └────────────┬─────────────┘
                                      │
                     ┌────────────────┼─────────────────────┐
                     ▼                ▼                      ▼
           ┌─────────────────┐ ┌──────────────┐   ┌───────────────────┐
           │ Orchestrator     │ │ Cache layer  │   │ Rate limiter       │
           │ (asyncio.gather  │ │ (SQLite,     │   │ (slowapi, 10/min   │
           │  parallel)       │ │  24h TTL)    │   │  per IP)           │
           └────────┬─────────┘ └──────────────┘   └───────────────────┘
                    │ fan-out to signal collectors (parallel, async)
     ┌───────────────┼────────────────┬────────────────┬──────────────┬─────────────┐
     ▼               ▼                ▼                ▼              ▼             ▼
┌────────┐   ┌───────────┐   ┌─────────────┐  ┌──────────────┐ ┌──────────────┐ ┌────────────┐
│ WHOIS/ │   │ SSL/TLS   │   │ DNS/Hosting │  │ Reputation   │ │ Content/HTML │ │ Typosquat/ │
│ RDAP   │   │ Certificate│  │ (ASN, geo)  │  │ (Safe Browsing│ │ Heuristics   │ │ Brand      │
│ Age    │   │            │   │             │  │  VirusTotal, │ │              │ │ Impersonatn│
│        │   │            │   │             │  │  URLhaus)    │ │              │ │            │
└────┬────┘   └─────┬─────┘   └──────┬──────┘  └──────┬───────┘ └───────┬──────┘ └─────┬──────┘
     └──────────────┴───────────────┴────────────────┴──────────────────┴──────────────┘
                                           │
                                           ▼
                              ┌────────────────────────┐
                              │  Scoring Engine          │
                              │  weighted rule-based,    │
                              │  blacklist hard-cap,     │
                              │  completeness factor     │
                              └────────────┬─────────────┘
                                           ▼
                              ┌────────────────────────┐
                              │  Response: score,       │
                              │  verdict, evidence list,│
                              │  LLM summary            │
                              └────────────────────────┘
```

## Design decisions

### 1. Rule-based scoring, LLM summary only
The numeric score is **deterministic** and built from real, live signals. An LLM (Groq, free tier) is used **only** to convert structured findings into a plain-English paragraph. This keeps the tool trustworthy and auditable: a hallucination in the score would undermine the entire product, whereas a summary drift is bounded and catchable. The prompt explicitly forbids the model from inventing findings or changing the verdict; any drift is treated as a prompt bug.

### 2. Fail-closed, confidence-aware output
A scan with little usable data is not “safe.” The scorer requires at least 5 of 8 checks to have completed before emitting a numeric score; otherwise the verdict is **Insufficient Data** with `score: null`. When scoring applies, the raw score is scaled by the completion ratio, so missing reputation/content checks structurally pull the score down rather than leaving it untouched.

### 3. Every collector is well-behaved
Each collector is an async function with an 8s hard timeout (enforced by `asyncio.wait_for` in the orchestrator), and always returns a `SignalResult` — it never raises past its own boundary. Timeouts, missing config, and hard failures are distinguished via `available` and `availability_reason` (`not_configured` / `error` / `dns_failure`). The UI renders these differently: config skips (⚙️/`!` + “Not configured”), failures (⚠️/`!`), and scored red flags (❌/`×`).

### 4. Blacklist hard-cap
If Google Safe Browsing or URLhaus flags the URL, the score is capped at max 40 → *High Risk*, regardless of how clean everything else looks. A good SSL cert must never offset an active phishing flag.

### 5. Caching before external calls
Results are cached by normalized domain in SQLite for 24h. This protects tight free-tier quotas (VirusTotal: 4 req/min, 500/day) and makes repeat lookups near-instant. Legacy cache rows without completeness metadata are invalidated rather than returned.

### 6. Keyless-by-default where possible
- Domain age uses **RDAP** (`rdap.org`) — free, no key, no signup — with `python-whois` as fallback.
- Hosting lookup uses **IPinfo** when a token is set and falls back to **ip-api.com** (keyless, non-commercial) otherwise.
- Reputation checks (Safe Browsing, VirusTotal, URLhaus) need keys; when a key is missing the check is marked `not_configured` (never treated as a pass).

## Data flow for a scan

1. `POST /scan` → normalize/validate URL (`utils.normalize_url`), extract registrable domain (`tldextract`).
2. Check SQLite cache (24h TTL); return cached result if fresh.
3. Fan out 8 collectors with `asyncio.gather`, each under an 8s timeout.
4. Any timeout/exception becomes an `available=False` stand-in; hard failures (e.g., DNS) are scored deductions.
5. `scoring/engine.py` computes raw score + completeness → `calculate_assessment` returns score/verdict/confidence.
6. `llm/summarizer.py` writes the summary (or templated fallback).
7. Assemble `ScanResult`, persist to cache, return.

## Failure-handling matrix

| Situation | Signal behavior |
|---|---|
| Collector times out (8s) | `available=False`, `availability_reason="error"`, no deduction |
| API key missing | `available=False`, `availability_reason="not_configured"` |
| Domain doesn't resolve (DNS) | `passed=False`, −25 deduction, still `available=True` |
| RDAP + WHOIS both fail | `available=False` (domain age unknown) |
| IPinfo down | falls back to `ip-api.com`; if both fail → `available=False` |
| Safe Browsing / URLhaus hit | `passed=False`, deduction + hard-cap to High Risk |
| Groq call fails | templated summary fallback |

## Future / V2 (explicitly out of MVP scope)
Bulk/CSV scanning, browser extension, scheduled re-checks + alerts, API-key business access, screenshot visual similarity. These are gated on Suproc PM review of the MVP.