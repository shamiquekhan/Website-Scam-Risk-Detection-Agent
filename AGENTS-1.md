# AGENTS.md

This file orients any AI coding agent (Claude Code, Cursor, Codex, etc.) working in this repository. Read this before making changes. It reflects the design decided in `docs/build-guide.md` and `docs/implementation-plan.md` — treat those as the source of truth for *why*; this file is the source of truth for *how to work in the codebase*.

---

## Project summary

Website Scam Risk Detector: user submits a URL, backend fan-outs to independent signal collectors (WHOIS, SSL, blacklists, DNS/hosting, content heuristics, typosquat check), a deterministic rule-based scoring engine combines them into a 0–100 score + verdict, and an LLM (Groq) writes a plain-English summary of the findings — **the LLM never sets or adjusts the score**.

---

## Repo layout

```
backend/app/
  main.py              FastAPI routes
  models.py            Pydantic schemas — read this first, everything else depends on it
  orchestrator.py       Fans out to collectors, assembles final ScanResult
  utils.py              URL normalization/validation
  collectors/            One file per signal, all follow the same async contract
  scoring/               weights.json (config) + engine.py (pure scoring logic)
  llm/summarizer.py       Groq call, summary-only
  cache/db.py             SQLite cache layer
backend/tests/            Unit tests per collector + calibration suite
backend/data/              top_brands.json, high_risk_asn.json
frontend/                Next.js app
docs/                     build-guide.md, implementation-plan.md, architecture.md, calibration-results.md
```

---

## Core invariants — do not violate these

1. **The numeric score is rule-based only.** Nothing in `llm/` is allowed to write to `ScanResult.score` or `ScanResult.verdict`. If you're touching scoring logic, it belongs in `scoring/engine.py` and should be traceable to a weight in `scoring/weights.json`.
2. **Every collector returns a `SignalResult`, never raises past its own function boundary.** Catch exceptions internally, set `available=False`. The orchestrator assumes this contract — don't make it defensive against collector exceptions, make the collectors well-behaved instead.
3. **Every collector has a hard timeout** (default 8s, set in the orchestrator's `asyncio.wait_for`). A slow third-party API must never block the whole scan.
4. **Deduction values live in `weights.json`, not hardcoded in collector files.** If a collector needs a new weight, add it to the config and reference it by key.
5. **Blacklist hard-cap rule:** if Google Safe Browsing or URLhaus flags the URL, `scoring/engine.py` must cap the verdict at "High Risk" regardless of the arithmetic total. Don't let this rule get refactored away silently.
6. **Never actively interact with live phishing/scam sites beyond a passive GET request.** No form submissions, no credential entry, no following payment flows, even in tests.
7. **Cache before you call.** Any new external API call must check the SQLite cache first (`cache/db.py`) and respect the 24h TTL — free-tier rate limits are tight (VirusTotal: 4/min, 500/day).

---

## Conventions

- **Language/style:** Python 3.11+, type hints everywhere, Pydantic v2 models for all data crossing a function boundary. Async for anything that does I/O.
- **Collector naming:** `backend/app/collectors/<signal_name>.py`, exposing a single `async def check(domain_or_url: str) -> SignalResult`.
- **Tests live next to what they test in intent, physically in `backend/tests/`, named `test_<module>.py`.**
- **No secrets in code.** All API keys read from environment variables via `python-dotenv`; `.env` is gitignored, `.env.example` lists every required key name with no values.
- **Frontend:** TypeScript, Tailwind, functional components only, no class components.

---

## How to run things

```bash
# Backend
cd backend && source venv/bin/activate
uvicorn app.main:app --reload          # dev server on :8000

# Backend tests
pytest backend/tests/ -v

# Calibration suite specifically (slow — hits live APIs)
pytest backend/tests/test_labeled_set.py -v

# Frontend
cd frontend && npm run dev             # dev server on :3000
```

---

## When adding a new signal collector

1. Add the weight(s) to `scoring/weights.json` first.
2. Create `collectors/<name>.py` following the existing contract (see `collectors/ssl_check.py` as the reference implementation — simplest one, no external API).
3. Write its unit test with at least one known-pass and one known-fail fixture.
4. Register it in `orchestrator.py`'s collector list.
5. Re-run the calibration suite (`test_labeled_set.py`) — a new collector can shift the false-positive/negative rate; don't merge if it regresses the numbers in `docs/calibration-results.md`.

## When touching the scoring engine

Any change to `scoring/engine.py` or `scoring/weights.json` requires re-running `test_labeled_set.py` and updating `docs/calibration-results.md` with the new numbers before considering the change done.

## When touching the LLM summarizer

Test with all three verdict bands (Safe/Caution/High Risk) manually — read the actual output, don't just check it doesn't error. Watch for the model inventing risks not present in the structured signals; the prompt explicitly forbids this, and any drift should be treated as a prompt bug, not a one-off model quirk to ignore.

---

## Out of scope for now (don't build unless asked)

Bulk/CSV scanning, browser extension, scheduled re-checks/alerts, API-key-gated business access, screenshot-based visual similarity. These are V2 (see `docs/build-guide.md` §3) and are gated on Suproc PM review of the MVP first.
