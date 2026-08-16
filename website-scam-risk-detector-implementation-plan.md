# Website Scam Risk Detector - Implementation Plan

Companion to `website-scam-risk-detector-build-guide.md`. That doc is the *what and why*; this doc is the *exact steps, in order, with checkboxes and code*. Work top to bottom - each step assumes the previous ones are done.

---

## 0. Prerequisites & environment setup

### 0.1 Accounts / API keys to acquire first (do this before writing any code)
- [ ] Google Cloud account → enable **Safe Browsing API** → generate API key (free)
- [ ] VirusTotal account → **API v3 key** from profile settings (free tier: 4 req/min, 500/day)
- [ ] PhishTank → no key strictly required for basic checks, but register for an "app key" to raise rate limits
- [ ] ipinfo.io account → free API token (50k requests/month) for ASN/geo lookups
- [ ] Groq account → API key for the summarizer LLM call
- [ ] Create a new GitHub repo: `website-scam-risk-detector` under `github.com/shamiquekhan`
- [ ] Create a `.env.example` file listing every key name (never commit real keys):
```
GOOGLE_SAFE_BROWSING_API_KEY=
VIRUSTOTAL_API_KEY=
PHISHTANK_APP_KEY=
IPINFO_TOKEN=
GROQ_API_KEY=
```

### 0.2 Local dev environment
- [ ] Python 3.11+ installed, `python --version` to confirm
- [ ] Node.js 20+ installed for frontend
- [ ] Create backend virtual env:
```bash
mkdir website-scam-risk-detector && cd website-scam-risk-detector
mkdir backend && cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
```
- [ ] `requirements.txt`:
```
fastapi==0.115.0
uvicorn[standard]==0.30.6
httpx==0.27.2
pydantic==2.9.2
python-whois==0.9.4
dnspython==2.6.1
beautifulsoup4==4.12.3
python-Levenshtein==0.26.0
groq==0.11.0
python-dotenv==1.0.1
slowapi==0.1.9
aiosqlite==0.20.0
pytest==8.3.3
pytest-asyncio==0.24.0
```
- [ ] `pip install -r requirements.txt`
- [ ] Verify FastAPI runs: create a throwaway `hello.py` with a `/ping` route, `uvicorn hello:app --reload`, confirm `200 OK` at `localhost:8000/ping`, then delete it.

---

## 1. Data models (build this first - everything else imports from here)

**File: `backend/app/models.py`**

- [ ] Define `SignalResult`:
```python
from pydantic import BaseModel
from typing import Optional, Any

class SignalResult(BaseModel):
    signal_name: str
    category: str            # "domain_trust" | "ssl" | "reputation" | "hosting" | "content" | "brand"
    passed: bool
    deduction: int
    detail: str
    raw_data: Optional[dict[str, Any]] = None
    available: bool = True   # False if the collector timed out/errored
```
- [ ] Define `ScanRequest`:
```python
class ScanRequest(BaseModel):
    url: str
```
- [ ] Define `ScanResult`:
```python
from datetime import datetime

class ScanResult(BaseModel):
    scan_id: str
    url: str
    normalized_domain: str
    score: int
    verdict: str              # "Safe" | "Caution" | "High Risk"
    summary: str
    signals: list[SignalResult]
    scanned_at: datetime
    cached: bool = False
```
- [ ] Write a quick `test_models.py` that instantiates each with dummy data to confirm no validation errors before moving on.

---

## 2. URL normalization & validation utility

**File: `backend/app/utils.py`**

- [ ] Function `normalize_url(raw: str) -> str`:
  - Strip whitespace
  - Add `https://` if no scheme present
  - Reject non-http(s) schemes (`javascript:`, `data:`, `file:`) - return `None`/raise `ValueError`
  - Lowercase the hostname portion only (not the path - paths are case-sensitive)
- [ ] Function `extract_domain(url: str) -> str` using `urllib.parse.urlparse` → return registrable domain (use `tldextract` library - add to requirements - so `www.sub.example.co.uk` → `example.co.uk`)
- [ ] Add `tldextract==5.1.2` to `requirements.txt`, reinstall
- [ ] Unit test: feed in 10 messy inputs (`"paypal-secure.com"`, `"HTTP://Example.COM/path"`, `"  https://test.com  "`, `"javascript:alert(1)"`) and assert expected normalized output / rejection.

---

## 3. Signal collectors - build and unit-test each independently

General pattern for every collector: async function, hard timeout, always returns a `SignalResult` (never raises past its own boundary - catch exceptions internally and set `available=False`).

### 3.1 SSL/TLS check
**File: `backend/app/collectors/ssl_check.py`**
- [ ] Use `ssl` + `socket` to open a connection to port 443, retrieve certificate via `getpeercert()`
- [ ] Extract: issuer, `notAfter` (expiry), validate hostname matches cert (via `ssl.match_hostname` or manual check)
- [ ] Deductions:
  - No HTTPS available at all / connection refused on 443 → `-20`, detail: "Site does not support HTTPS - no encryption for any data you enter."
  - Cert expired or expires within 7 days → `-15`
  - Cert valid but self-signed / hostname mismatch → `-20`
  - Otherwise `passed=True, deduction=0`
- [ ] Test against: `google.com` (pass), a site you know has an expired cert (search "expired ssl test site" - use a dedicated test site, e.g. `expired.badssl.com`), `self-signed.badssl.com` (badssl.com is a public test-fixture site made exactly for this)

### 3.2 WHOIS / domain age (RDAP preferred)
**File: `backend/app/collectors/whois_check.py`**
- [ ] Primary: query `https://rdap.org/domain/{domain}` via `httpx` (free, no key, structured JSON)
- [ ] Fallback: `python-whois` library if RDAP has no data for that TLD
- [ ] Parse creation date, compute `days_old`
- [ ] Deductions per weights table in the build guide (`-25` if `<30` days, `-12` if `30-180` days)
- [ ] Also capture registrar name and whether registrant is privacy-masked (store in `raw_data`, used later by content/brand logic, not scored directly unless payment forms are also present - cross-signal logic lives in the scoring engine, not here)
- [ ] Test against a very new domain (find one via a "newly registered domains" list) and an old established one (`wikipedia.org`)

### 3.3 DNS + hosting/ASN
**File: `backend/app/collectors/dns_hosting.py`**
- [ ] Use `dnspython` to resolve A record → IP
- [ ] Call `ipinfo.io/{ip}?token=...` for ASN, org, country
- [ ] Maintain a small `data/high_risk_asn.json` list you seed manually from public "bulletproof hosting" writeups (start with a short list of 10-15, expand later - don't try to be exhaustive on day one)
- [ ] Deduction if ASN is in that list, or if there are zero MX records + the domain claims to be a business (weak signal, keep deduction small, `-5`)
- [ ] Test against a normal corporate site and note the ASN/country returned, sanity-check it looks right

### 3.4 Google Safe Browsing
**File: `backend/app/collectors/safe_browsing.py`**
- [ ] `POST` to `https://safebrowsing.googleapis.com/v4/threatMatches:find?key=...` with the URL in the body, threat types `MALWARE`, `SOCIAL_ENGINEERING`, `UNWANTED_SOFTWARE`
- [ ] If `matches` non-empty → `deduction=40`, `passed=False`
- [ ] Test with Google's official test URL for this API: `http://testsafebrowsing.appspot.com/s/malware.html` (documented test fixture - safe to call, designed for this)

### 3.5 VirusTotal
**File: `backend/app/collectors/virustotal.py`**
- [ ] `POST` URL for scanning (v3: submit → then `GET /urls/{id}` for the report; v3 uses URL-safe-base64 of the URL as the ID, or use the analysis endpoint)
- [ ] Count `malicious` + `suspicious` engine verdicts from `last_analysis_stats`
- [ ] Deduction scaled: `≥3` engines flagged → `-30`; `1-2` → `-10`
- [ ] Respect the 4/min free-tier limit - add a small internal delay/queue if you expect to hit this during testing
- [ ] Test against a known EICAR-adjacent test resource or a URL you've already seen flagged in VT's public UI

### 3.6 PhishTank
**File: `backend/app/collectors/phishtank.py`**
- [ ] `POST` to PhishTank's `checkurl` endpoint with the URL
- [ ] If `in_database=true` and `valid=true` → `deduction=35`
- [ ] Test with a phishing URL pulled live from PhishTank's own public feed (they publish a "verified phish" CSV/JSON feed - pull one entry at test time so it's current, don't hardcode an old one that may be taken down)

### 3.7 Content/HTML heuristics
**File: `backend/app/collectors/content_heuristics.py`**
- [ ] Fetch page with `httpx` (timeout 8s, follow redirects, cap at 5 hops, record the redirect chain)
- [ ] Deduction if final domain ≠ entered domain and it's a cross-domain redirect (`-12`)
- [ ] Parse HTML with BeautifulSoup:
  - Find `<form>` elements with `type="password"` input → check if page itself is HTTPS (already known from 3.1) → deduction `-20` if password form on non-HTTPS
  - Keyword scan on visible text for urgency phrases (build a list: "verify your account", "act now", "suspended", "confirm immediately", "unusual activity") - only deduct if **combined** with a form present (`-10`), not on keyword alone, to avoid penalizing legitimate security pages
- [ ] Test against a normal e-commerce login page and confirm no false-positive on the password-form check when HTTPS is present

### 3.8 Typosquat / brand impersonation
**File: `backend/app/collectors/typosquat.py`**
**File: `backend/data/top_brands.json`**
- [ ] Build `top_brands.json`: array of ~200 canonical domains - start with a manageable seed list of ~40-50 (major banks, PayPal, Amazon, Microsoft, Google, Apple, top e-commerce/payment brands relevant to your likely user base in India + globally) and note in the README this list is expandable
- [ ] For each brand domain, compute Levenshtein distance from the scanned domain; also check common homoglyph substitutions (`0`/`o`, `1`/`l`, `rn`/`m`) and hyphen-insertion patterns (`paypal.com` → `paypal-secure.com`)
- [ ] If distance ≤ 2 from a known brand **and** the scanned domain is not the brand's actual domain → `-30`, detail names which brand it resembles
- [ ] Test cases: `paypa1.com`, `arnazon.com`, `microsoft-support-verify.com` (fabricated for testing only, don't register/visit) - write these as pure string inputs to the function, not live URLs, since the function should be testable without a network call

---

## 4. Scoring engine

**File: `backend/app/scoring/weights.json`** - externalize every deduction value from section 3 into this config so tuning doesn't require code changes.

**File: `backend/app/scoring/engine.py`**
- [ ] Function `calculate_score(signals: list[SignalResult]) -> tuple[int, str]`:
  - Start at 100
  - Sum all `deduction` values from signals where `available=True`
  - Apply hard-cap rule: if Safe Browsing or PhishTank `passed=False`, force final score to max 40 regardless of arithmetic result
  - Floor at 0, ceiling at 100
  - Map to verdict band (80-100 Safe / 50-79 Caution / 0-49 High Risk)
- [ ] Unit test with hand-crafted signal lists covering: all-pass (expect ~100/Safe), one hard blacklist hit with everything else clean (expect capped High Risk), mixed moderate flags (expect Caution)

---

## 5. LLM summarizer (Groq) - summary only, never touches the score

**File: `backend/app/llm/summarizer.py`**
- [ ] Build a strict prompt template that:
  - Passes in the full structured signal list + score + verdict as **given facts**
  - Instructs the model explicitly: "Do not invent additional risks. Do not change the verdict. Summarize only the findings provided, in 2-4 plain-English sentences for a non-technical reader."
- [ ] Call Groq's chat completion endpoint with a small/fast model (e.g. Llama 3.1 8B) for low latency
- [ ] Wrap in try/except - if the LLM call fails or times out, fall back to a templated summary built from string formatting (never let the whole scan fail because the summary step failed)
- [ ] Test: feed it 3 different signal sets (all-clear, mixed, high-risk) and manually read the output for accuracy and tone.

---

## 6. Orchestrator

**File: `backend/app/orchestrator.py`**
- [ ] `async def run_scan(url: str) -> ScanResult`:
  1. Normalize/validate URL (section 2) - raise `400` upstream if invalid
  2. Check cache (section 7) - return cached result if fresh
  3. `asyncio.gather(*collectors, return_exceptions=True)` with each collector wrapped in `asyncio.wait_for(..., timeout=8)`
  4. Any collector that times out or raises → build a `SignalResult(available=False, ...)` stand-in so scoring still works
  5. Pass all signals to `calculate_score`
  6. Pass signals + score + verdict to `summarizer`
  7. Assemble `ScanResult`, write to cache, return
- [ ] Integration test: run `run_scan("https://www.wikipedia.org")` end-to-end locally and print the full result - this is your first real full-pipeline smoke test.

---

## 7. Caching layer

**File: `backend/app/cache/db.py`**
- [ ] SQLite table `scans(scan_id TEXT PK, domain TEXT, result_json TEXT, created_at TIMESTAMP)`
- [ ] `get_cached(domain) -> ScanResult | None` - return only if `created_at` within last 24h
- [ ] `save_scan(result: ScanResult)`
- [ ] Index on `domain` for fast lookup
- [ ] Test: run the same URL twice through the orchestrator, confirm the second call returns `cached=True` and is near-instant

---

## 8. FastAPI app & routes

**File: `backend/app/main.py`**
- [ ] `POST /scan` - body `ScanRequest` → calls orchestrator → returns `ScanResult`
  - [ ] Add `slowapi` rate limiting: 10 requests/minute per IP
  - [ ] Return `422` for malformed URLs with a clear error message
- [ ] `GET /scan/{scan_id}` - look up a past result by ID for the shareable-report frontend page
- [ ] `GET /health` - simple liveness check for deployment monitoring
- [ ] Enable CORS for your frontend's deployed domain (and `localhost:3000` for dev)
- [ ] Run locally: `uvicorn app.main:app --reload`, hit `/scan` with `curl` or the FastAPI auto-docs at `/docs`, confirm full round-trip works

---

## 9. Calibration test suite (do not skip this phase)

**File: `backend/tests/test_labeled_set.py`**
- [ ] Build `tests/fixtures/known_good.json` - 15-20 legitimate URLs (major banks, e-commerce, gov, established SaaS)
- [ ] Build `tests/fixtures/known_bad.json` - 15-20 currently-live phishing URLs pulled from PhishTank/OpenPhish public feeds at test-run time (fetch dynamically in the test setup rather than hardcoding, since phishing URLs get taken down fast)
- [ ] Test asserts: known-good average score ≥ 80, known-bad average score ≤ 49, and report per-URL results in a markdown table
- [ ] Run the suite, inspect failures, adjust `weights.json`, re-run - iterate until false-positive/false-negative rate is acceptable
- [ ] Save final results to `docs/calibration-results.md` with the numbers - this is your evidence of rigor for Suproc

---

## 10. Frontend

- [ ] `npx create-next-app@latest frontend --typescript --tailwind --app`
- [ ] `frontend/app/page.tsx` - URL input form, calls `POST {BACKEND_URL}/scan`, shows loading spinner, then renders result
- [ ] `frontend/components/ScoreCard.tsx` - big number + colored verdict badge (green/yellow/red) + LLM summary text
- [ ] `frontend/components/SignalList.tsx` - expandable accordion, one row per signal: ✅/⚠️/❌ icon, signal name, detail text
- [ ] `frontend/app/report/[id]/page.tsx` - fetches `GET /scan/{id}` for shareable permalinks
- [ ] Add `.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000` for dev
- [ ] Handle states: empty, loading, success, error (invalid URL, backend down, rate-limited)
- [ ] Basic responsive layout - this will be viewed on phones during the demo/pitch

---

## 11. Deployment

- [ ] Backend → Render or Railway free tier: connect GitHub repo, set build command `pip install -r requirements.txt`, start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, add all env vars from `.env.example` in the dashboard
- [ ] Frontend → Vercel: connect repo, set `NEXT_PUBLIC_API_URL` to the deployed backend URL
- [ ] Confirm CORS allows the deployed frontend origin
- [ ] Run the full calibration test suite one more time against the **deployed** backend to catch any environment-specific issues (missing env var, different timeout behavior)
- [ ] Set up basic uptime check (e.g., a free UptimeRobot monitor on `/health`) so the demo link doesn't silently die before a Suproc review

---

## 12. Documentation & packaging for Suproc

- [ ] `README.md`: problem statement, architecture diagram (reuse from build guide), setup instructions, API docs, calibration results summary, screenshots, live demo link
- [ ] `docs/architecture.md`: expanded version of the diagram + design rationale (why rule-based scoring, why LLM is summary-only)
- [ ] `docs/calibration-results.md`: from step 9
- [ ] Record 2-3 minute demo video: scan a known-safe site, then a known-risky one, narrate the signal breakdown
- [ ] Write the Marketplace listing copy (short pitch, target user, link to demo + repo)
- [ ] Send to Suproc PM for review

---

## Suggested order of execution (checklist of checklists)

1. [ ] Section 0 - environment & keys
2. [ ] Section 1 - models
3. [ ] Section 2 - URL utils
4. [ ] Section 3.1-3.8 - collectors, one at a time, each tested before moving to the next
5. [ ] Section 4 - scoring engine
6. [ ] Section 5 - summarizer
7. [ ] Section 6 - orchestrator (first real end-to-end smoke test happens here)
8. [ ] Section 7 - caching
9. [ ] Section 8 - API routes
10. [ ] Section 9 - calibration suite, tune weights
11. [ ] Section 10 - frontend
12. [ ] Section 11 - deploy
13. [ ] Section 12 - docs & Suproc handoff
