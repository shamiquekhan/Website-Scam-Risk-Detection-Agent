# Website Scam Risk Detector Agent

A standalone proof-of-work agent that takes a URL and returns a **risk score (0–100)**, a **verdict** (Safe / Caution / High Risk / Insufficient Data), and a **signal-by-signal explanation** of why — in under ~15 seconds, no login required.

Built as a marketplace showcase: deterministic, auditable, and cheap to run on free tiers.

## What it does

- User submits a URL/domain.
- The backend fans out to independent **signal collectors** in parallel:
  - SSL/TLS certificate validity & expiry
  - RDAP/WHOIS domain age (keyless RDAP, `python-whois` fallback)
  - DNS resolution + hosting ASN/geo (IPinfo, `ip-api.com` fallback)
  - Google Safe Browsing
  - VirusTotal
  - URLhaus (malware/phishing URL database)
  - Content heuristics (password form over non-HTTPS, cross-domain redirects, urgency language + form)
  - Typosquat / brand-impersonation check
- A **deterministic weighted scoring engine** combines them into a 0–100 score + verdict.
- An LLM (Groq) writes a plain-English summary. **The LLM never sets or changes the score.**

Key safety property: the score is **fail-closed**. If too few checks return real data (>4 unavailable), the tool returns **“Insufficient Data”** instead of a false-precision number, and a completeness factor scales the score so missing evidence cannot make a site look safe.

---

## Architecture

```
Frontend (Next.js/Tailwind)
        │ POST /scan {url}
        ▼
FastAPI Backend → cache (SQLite, 24h) → rate limit (slowapi)
        │ fan-out (asyncio.gather, 8s per collector timeout)
        ▼
[SSL] [WHOIS/RDAP] [DNS/Hosting] [Safe Browsing] [VirusTotal] [URLhaus] [Content] [Typosquat]
        ▼
Scoring engine (weighted deductions, blacklist hard-cap, completeness factor)
        ▼
Response: score, verdict, evidence list, LLM summary
```

Rule-based scoring is deliberate: every point deducted traces to a named, inspectable reason, so the tool is audit-friendly and never “hallucinates” a score.

---

## Repo layout

```
backend/
  app/
    main.py              FastAPI routes (/scan, /scan/{id}, /health)
    models.py            Pydantic schemas
    orchestrator.py      Collector fan-out + assembly
    utils.py             URL normalization/validation
    collectors/          One file per signal collector
    scoring/engine.py    Weighted scoring + confidence/completeness
    llm/summarizer.py     Groq summary (summary-only)
    cache/db.py           SQLite 24h cache
  data/                  top_brands.json, high_risk_asn.json
  tests/                 Unit tests + calibration suite
  .env.example           Lists required env vars (no real values)
frontend/
  app/  page.tsx (scan), report/[id].tsx (shareable report)
  components/ScoreCard.tsx, SignalList.tsx
docs/
  architecture.md, calibration-results.md
```

---

## How to run locally

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill in your API keys
uvicorn app.main:app --reload   # http://127.0.0.1:8000
```

Run the tests:

```bash
pytest tests/ -v
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # or set NEXT_PUBLIC_API_URL
npm run dev                        # http://127.0.0.1:3000
```

---

## API

### `POST /scan`

Body: `{ "url": "https://example.com" }`

Returns a `ScanResult`:

| Field | Type | Meaning |
|---|---|---|
| `score` | `int | null` | 0–100, `null` when evidence is insufficient |
| `verdict` | `str` | `Safe` / `Caution` / `High Risk` / `Insufficient Data` |
| `signals` | `array` | Each signal: `{signal_name, category, passed, deduction, detail, available, availability_reason}` |
| `completed_signals` | `int` | Number of checks that returned real data |
| `total_signals` | `int` | Total checks attempted |
| `confidence` | `int` | `completed/total * 100` |
| `summary` | `str` | Plain-English LLM summary (falls back to templated text if Groq is unavailable) |

Verdict bands (when scoring applies):
- **80–100 → Safe** (green)
- **50–79 → Caution** (yellow)
- **0–49 → High Risk** (red)
- **Insufficient Data** → fewer than 5 of 8 checks completed

### `GET /scan/{scan_id}`

Retrieve a past scan by ID for shareable report links.

### `GET /health`

Liveness probe for deployment monitoring.

---

## Environment variables

All keys go in `backend/.env` (never committed). See `backend/.env.example`.

| Variable | Used for | Notes |
|---|---|---|
| `GOOGLE_SAFE_BROWSING_API_KEY` | Safe Browsing | Non-commercial use; create via Google Cloud Console |
| `VIRUSTOTAL_API_KEY` | VirusTotal | Free tier: 4 req/min, 500/day |
| `URLHAUS_AUTH_KEY` | URLhaus | Free community API (abuse.ch) |
| `IPINFO_TOKEN` | Hosting geo/ASN | Optional — falls back to keyless `ip-api.com` |
| `GROQ_API_KEY` | Summary only | Falls back to templated summary if absent |

RDAP (`rdap.org`) and `ip-api.com` need **no key**.

---

## Scoring model

Starts at 100 and deducts per weighted rule (see `backend/app/scoring/weights.json`). Examples:

- Domain age < 30 days → −25
- No/expired/invalid HTTPS → −15 to −20
- Safe Browsing hit → −40
- URLhaus hit → −35
- VirusTotal ≥3 engines → −30
- Typosquat of a top-brand → −30
- DNS resolution failure → −25

Hard-cap: any Safe Browsing or URLhaus hit caps the outcome at *High Risk* regardless of other signals. Completeness scaling ensures missing checks pull scores down and can trigger *Insufficient Data*.

---

## Feature status

Implemented (MVP):
- All 8 collectors, deterministic scoring, completeness/confidence gating
- Shareable reports, caching, rate limiting, UI with verdict + signal breakdown
- Fail-closed scoring; URLhaus replacing the now-defunct PhishTank key system

V2 (out of MVP scope, pending Suproc review):
- Bulk/CSV scanning, browser extension, scheduled re-checks/alerts, API-key business access, screenshot visual similarity.

---

## Live calibration

`docs/calibration-results.md` documents the methodology and current status. Known-legitimate and known-phishing test sets are still being validated live before final numbers are recorded.