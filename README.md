# ScamShield AI — Website Scam Risk Detector Agent

> **Zero-cost, zero-API-key, multi-signal website safety scanner.** 11 independent
> checks — SSL, domain age, DNS/hosting, OpenPhish, URLhaus, a **local on-device ML
> phishing classifier**, URL-structure heuristics, content heuristics, and
> typosquatting — combined by a deterministic weighted engine into a **0–100 risk
> score** + verdict in under ~10 seconds.

Built as a marketplace showcase: **$0 to build, $0 to run**, fully auditable, and
fail-closed by design. See [`docs/FREE_STACK.md`](docs/FREE_STACK.md) for why every
dependency is free.

## What it does

- User submits a URL (single or up to 100 in a batch).
- The backend fans out to **11 signal collectors** in parallel:

  | Signal | Source | Key? |
  |--------|--------|------|
  | SSL/TLS validity & expiry | Direct TLS handshake | — |
  | Domain age | Keyless IANA RDAP bootstrap + `rdap.org` + `python-whois` | — |
  | DNS + hosting ASN/geo | `dns.resolver` + `ip-api.com` + `ipwho.is` | — |
  | **OpenPhish feed** | Public feed, refreshed every 6h | — |
  | **URLhaus blocklist** | Keyless public download, refreshed daily | — |
  | **Local ML classifier** | ONNX model (on-device) | — |
  | URL-structure heuristics | Deterministic rules | — |
  | Content heuristics | Page fetch + `BeautifulSoup` | — |
  | Typosquat / brand impersonation | Local `top_brands.json` + Levenshtein | — |
  | Google Safe Browsing | Optional key | optional |
  | VirusTotal | Optional key | optional |

- A **deterministic weighted scoring engine** combines them into a 0–100 score + verdict.
- An LLM writes a plain-English summary — **Ollama locally** by default, Groq or a
  templated summary as fallback. **The LLM never sets or changes the score.**

Key safety property: the score is **fail-closed**. If fewer than 6 of 11 checks
return real data, the tool returns **“Insufficient Data”** instead of a
false-precision number, and a completeness factor scales the score so missing
evidence cannot make a site look safe.

---

## Architecture

```
Frontend (Next.js/Tailwind, dark mode)
        │ POST /scan {url}  |  POST /scan/batch {urls[]}
        ▼
FastAPI Backend → SQLite 24h cache → slowapi rate limit
        │ fan-out (asyncio.gather, 8s per collector timeout)
        ▼
[SSL] [WHOIS/RDAP] [DNS/Hosting] [OpenPhish] [URLhaus] [SafeBrowsing*] [VirusTotal*]
[Local ML (ONNX)] [URL structure] [Content] [Typosquat]
        ▼
Scoring engine (weights v2, blacklist hard-cap, completeness factor)
        ▼
Ollama (local) → Groq → templated  LLM summary
        ▼
Response: score, verdict, evidence list, summary
```

Full diagram and design notes: [`docs/architecture.md`](docs/architecture.md).

---

## Repo layout

```
backend/
  app/
    main.py              FastAPI routes (/scan, /scan/batch, /scan/{id}, /health)
    models.py            Pydantic schemas
    orchestrator.py      Collector fan-out + assembly + batch runner
    utils.py             URL normalization + path-aware feed matching
    collectors/          One file per signal collector (11 total)
    scoring/engine.py    Weighted scoring + verdict bands + completeness
    llm/summarizer.py    Ollama → Groq → templated summary
    ml/                  feature_extractor.py + inference.py (ONNX runtime)
    cache/db.py          SQLite 24h cache
  ml_training/           fetch_data → features → train → evaluate → export_onnx
  models/                phishing_classifier.onnx (bundled)
  data/                  top_brands.json, high_risk_asn.json (+ cached feeds)
  tests/                 pytest suite
  Dockerfile, docker-compose.yml (with Ollama)
frontend/
  app/  page.tsx (scan), batch/ (bulk scan), report/[id] (shareable report)
  components/ ScoreCard (animated gauge), SignalList, LoadingSkeleton
docs/  architecture.md, FREE_STACK.md, calibration-results.md
.github/workflows/ci.yml   GitHub Actions (backend tests + frontend build)
render.yaml               Free-tier Render blueprint (backend + Ollama)
```

---

## How to run locally

### Backend (no API keys required)

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload   # http://127.0.0.1:8000
```

Run the tests:

```bash
pytest tests/ -v
```

Optional — local LLM summarizer with Ollama:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull phi3:mini          # or llama3.2:3b
# OLLAMA_MODEL=phi3:mini uvicorn app.main:app
```

Optional — retrain the ML classifier (model is bundled, so usually unnecessary):

```bash
pip install -r requirements-train.txt
python -m ml_training.fetch_data   # OpenPhish + Majestic
python -m ml_training.train        # Random Forest → .pkl
python -m ml_training.export_onnx  # → models/phishing_classifier.onnx
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL if needed
npm run dev                        # http://127.0.0.1:3000
```

### Docker (backend + Ollama)

```bash
cd backend
docker compose up --build -d
```

---

## API

### `POST /scan`

Body: `{ "url": "https://example.com" }`

Returns a `ScanResult`:

| Field | Type | Meaning |
|---|---|---|
| `score` | `int | null` | 0–100, `null` when evidence is insufficient |
| `verdict` | `str` | `Safe` / `Likely Safe` / `Caution` / `Suspicious` / `High Risk` / `Insufficient Data` |
| `signals` | `array` | Each: `{signal_name, category, passed, deduction, detail, available, availability_reason}` |
| `completed_signals` | `int` | Checks that returned real data |
| `total_signals` | `int` | Total checks attempted (11) |
| `confidence` | `int` | `completed/total * 100` |
| `summary` | `str` | Plain-English summary |

### `POST /scan/batch`

Body: `{ "urls": ["https://a.com", "https://b.com"], "max_concurrency": 4 }` (≤100 URLs)
Returns `{ results[], scanned, failed, errors[] }`.

### `GET /scan/{scan_id}` · `GET /health`

Shareable report retrieval · liveness probe.

---

## Verdict bands (weights v2)

| Score | Verdict |
|-------|---------|
| 90–100 | Safe (green) |
| 70–89 | Likely Safe (light green) |
| 50–69 | Caution (yellow) |
| 30–49 | Suspicious (orange) |
| 0–29 | High Risk (red) |
| < 6 of 11 checks | Insufficient Data |

Hard-cap: any OpenPhish / URLhaus / Safe Browsing hit caps the outcome at
High Risk regardless of other signals. Completeness scaling ensures missing
checks pull scores down and can trigger Insufficient Data.

---

## Environment variables

All keys are **optional**. See `backend/.env.example`.

| Variable | Used for | Notes |
|---|---|---|
| `VIRUSTOTAL_API_KEY` | VirusTotal signal | Optional |
| `GOOGLE_SAFE_BROWSING_API_KEY` | Safe Browsing signal | Optional; OpenPhish is the keyless default |
| `URLHAUS_AUTH_KEY` | URLhaus authenticated API | Optional; keyless blocklist is the default |
| `IPINFO_TOKEN` | Hosting geo/ASN via IPinfo | Optional; `ip-api.com` / `ipwho.is` fallbacks |
| `GROQ_API_KEY` | Second LLM summarizer fallback | Optional; Ollama is the default |
| `OLLAMA_BASE_URL` | Local LLM endpoint | Default `http://localhost:11434` |
| `OLLAMA_MODEL` | Local LLM model | Default `phi3:mini` |
| `SCAN_DB_PATH` | SQLite cache path | Default `cache.db` |

---

## Feature status

Implemented:
- 11 collectors (OpenPhish + URLhaus keyless feeds, local ONNX ML classifier,
  URL-structure heuristics), deterministic scoring (weights v2, 5 verdict bands),
  completeness/confidence gating, shareable reports, 24h caching, rate limiting,
  batch scanning, dark-mode UI with animated score gauge, Ollama-first summaries.

V2 (out of scope, pending review):
- Browser extension, scheduled re-checks/alerts, screenshot visual similarity,
  API-key business tier.

---

## Calibration

See [`docs/calibration-results.md`](docs/calibration-results.md) for methodology
and the latest results, including the local ML model's holdout precision/recall.

---

## License

MIT — free for commercial and personal use. Attribution appreciated.

*100% free. 100% open-source. 100% auditable. No API keys required.*