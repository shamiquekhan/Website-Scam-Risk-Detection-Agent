# Website Scam Risk Detector — Full Build Guide

**Category:** IT
**Target platform:** Suproc Marketplace (standalone proof-of-work agent)
**Author:** Shamique
**Status:** Build guide v1 — start to finish

---

## 1. What this agent does

A user pastes a URL (or domain). The agent returns a **risk score (0–100)**, a **verdict** (Safe / Caution / High Risk), and a **breakdown of every signal** that produced that score — in under ~15 seconds, with no login required to try it.

It answers the question a non-technical buyer, supplier, or SME owner actually has before they pay a stranger's website or click a link someone sent them:

> "Is this site legit, or is it going to scam me?"

This is deliberately **not** a Suproc-internal supplier-matching tool — it's a self-contained trust/safety utility anyone can use on any website, which is why it clears the "standalone proof-of-work" bar the PM set.

---

## 2. Why this scores well as a Marketplace showcase

- **Instantly understandable** — no domain expertise needed to see the value in one demo.
- **Real, checkable data** — every claim in the score is backed by a live signal (WHOIS age, SSL validity, blacklist hits), not an LLM guess. This builds trust in the output itself.
- **Cheap to run** — almost entirely free-tier APIs, so a live public demo doesn't burn budget.
- **Extensible** — natural upsell path (bulk scanning, browser extension, API-for-business, monitoring/alerts) which is attractive to Suproc's "prove capability → get client work" model.
- **Fast to build** — MVP is achievable in days, not weeks, because most of the hard work is calling well-documented third-party APIs and combining scores, not training models.

---

## 3. Scope

### MVP (what you demo first)
- Single URL input → risk score + verdict + signal breakdown.
- Checks: domain age/WHOIS, SSL certificate validity, DNS/hosting red flags, blacklist/reputation lookups (Google Safe Browsing, VirusTotal, PhishTank), basic content heuristics (login-form-on-non-HTTPS, excessive redirects, suspicious keywords), typosquatting/brand-impersonation check against a list of common targets (PayPal, banks, popular e-commerce).
- Clean web UI + shareable JSON/report.

### V2 (post-approval, roadmap only — don't over-build before Suproc sign-off)
- Bulk CSV upload / batch scanning.
- Scheduled re-checks + email alert if a previously-safe site's score drops.
- Browser extension.
- API access with API keys for businesses to embed the checker in their own checkout/onboarding flows.
- Screenshot-based visual similarity detection (compare against known brand login pages).

**Rule for this build:** ship MVP end-to-end first, get Suproc's PM to review it live, then decide on V2 scope. Don't build V2 features before that checkpoint — same mistake pattern as the rejected first idea (scope crept beyond what was asked).

---

## 4. Architecture overview

```
                         ┌─────────────────────────┐
                         │   Frontend (Next.js/     │
                         │   simple React + Tailwind)│
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
           │ (LangGraph or    │ │ (Redis/SQLite│   │ (per-IP, per-URL)  │
           │  plain async     │ │  24h TTL)    │   │                    │
           │  pipeline)       │ └──────────────┘   └───────────────────┘
           └────────┬─────────┘
                     │ fan-out to signal collectors (parallel, async)
     ┌───────────────┼────────────────┬────────────────┬─────────────────┬─────────────────┐
     ▼               ▼                ▼                ▼                 ▼                 ▼
 ┌────────┐    ┌───────────┐   ┌─────────────┐  ┌──────────────┐ ┌───────────────┐ ┌───────────────┐
 │ WHOIS/  │    │ SSL/TLS   │   │ Blacklist/   │  │ DNS/Hosting  │ │ Content/HTML   │ │ Typosquat/     │
 │ Domain  │    │ Certificate│   │ Reputation   │  │ Signals      │ │ Heuristics     │ │ Brand-impersona│
 │ Age     │    │ Check      │   │ (Safe Browsing│  │ (age, ASN,   │ │ (forms, scripts│ │ tion check     │
 │         │    │            │   │ VirusTotal,  │  │  registrar   │ │ redirects,     │ │ (Levenshtein   │
 │         │    │            │   │ PhishTank)   │  │  country)    │ │ keywords)      │ │ vs known brands)│
 └────┬────┘    └─────┬─────┘   └──────┬───────┘  └──────┬───────┘ └───────┬────────┘ └───────┬────────┘
      └────────────────┴────────────────┴─────────────────┴─────────────────┴──────────────────┘
                                          │
                                          ▼
                             ┌────────────────────────┐
                             │  Scoring Engine          │
                             │  (weighted rule-based    │
                             │   + optional LLM summary)│
                             └────────────┬─────────────┘
                                          ▼
                             ┌────────────────────────┐
                             │  Response: score,        │
                             │  verdict, evidence list,  │
                             │  plain-English summary    │
                             └────────────────────────┘
```

**Key design decision:** the score itself is **rule-based and deterministic**, built from real signals. An LLM (Groq/free-tier model, consistent with your ARAMS stack) is used **only** to turn the structured findings into a plain-English summary paragraph — never to invent or adjust the numeric score. This keeps the tool trustworthy and auditable, which matters a lot for a "scam detector" — if the score itself were LLM-generated, one hallucination undermines the whole product's credibility.

---

## 5. Tech stack (optimized for free-tier, matches your existing setup)

| Layer | Choice | Why |
|---|---|---|
| Orchestration | Plain async Python (`asyncio.gather`) for MVP; LangGraph if you want it to look like a fork of ARAMS | Signal collectors are independent — no complex agent reasoning needed, so don't over-engineer with LangGraph unless you want the portfolio consistency |
| Backend | FastAPI | Async-native, fast to build, easy to deploy free (Render/Railway/Fly.io free tier) |
| LLM (summary only) | Groq (Llama 3.1/3.3 free tier) | Already in your stack from ARAMS |
| Cache | SQLite (MVP) → Redis (if you add scheduling/V2) | Avoid re-hitting rate-limited APIs for the same URL within 24h |
| Frontend | Next.js + Tailwind, or plain React + Vite | Simple single-page form + results view |
| Hosting | Vercel (frontend) + Render/Railway free tier (backend) | Zero-cost demo hosting |
| Repo | github.com/shamiquekhan | Consistent with existing portfolio |

---

## 6. Data sources / APIs (all have free tiers)

| Signal | Source | Free tier notes |
|---|---|---|
| Domain age, registrar, creation date | WHOIS (via `python-whois` lib or WhoisXML API free tier / RDAP) | RDAP (`rdap.org`) is free and unlimited, no key needed — prefer this over paid WHOIS APIs |
| SSL/TLS certificate validity, issuer, expiry | Python `ssl`/`OpenSSL` direct socket check | No API needed — connect directly, fully free |
| Malware/phishing blacklist | Google Safe Browsing API | Free, needs Google Cloud API key, generous quota |
| Multi-engine reputation | VirusTotal API v3 | Free tier: 4 requests/min, 500/day — enough for a demo with caching |
| Phishing-specific database | PhishTank API | Free, no key required for basic lookups |
| DNS records, hosting ASN/country | `dnspython` + free IP-to-ASN lookup (e.g., ipinfo.io free tier, 50k/month) | Flags hosting in high-abuse ASNs, mismatched country vs claimed business |
| Redirect chain, final URL, HTML content | `httpx`/`requests` + `BeautifulSoup` | Free, self-hosted, no external API |
| Typosquat/brand impersonation | Self-built: Levenshtein distance + homoglyph check against a curated list (~200 top brands: banks, payment processors, major e-commerce, popular SaaS) | Free, no API — this is a genuinely useful differentiator to build well |
| Optional: page screenshot for visual review (V2) | Apify actor (screenshot) or `playwright` self-hosted | Apify per your team's guidance to consider it; playwright is fully free if self-hosted |

**Note on Apify:** Suproc suggested Apify for APIs. For this project, most core signals don't need Apify (WHOIS/SSL/DNS are cheaper done directly). Reserve Apify for V2 (screenshotting, or scraping a scam-report site like ScamAdviser community reports if you want an extra corroborating signal) — mentioning this consideration in your write-up to Suproc shows you evaluated it rather than ignored it.

---

## 7. Scoring model (the core IP of this agent)

Design it as a **weighted deduction model** starting from 100 (perfectly safe) and subtracting points per red flag, floored at 0. Keep weights in a single config file so they're easy to tune after real-world testing.

### Suggested signal weights (starting point — tune after testing on known-good and known-scam sites)

| Category | Signal | Max deduction |
|---|---|---|
| Domain trust | Domain age < 30 days | -25 |
| Domain trust | Domain age 30–180 days | -12 |
| Domain trust | Privacy-protected WHOIS (masked owner) on a site requesting payment | -8 |
| SSL | No HTTPS / invalid certificate | -20 |
| SSL | Certificate expires in < 7 days, or free/short-lived cert (e.g. 90-day) on a site claiming to be a large business | -5 |
| Reputation | Flagged by Google Safe Browsing | -40 (near-instant high risk) |
| Reputation | Flagged by ≥3 VirusTotal engines | -30 |
| Reputation | Present in PhishTank | -35 |
| Hosting | Hosted on ASN with high abuse history / bulletproof hosting indicators | -10 |
| Hosting | Server country mismatches claimed business location (e.g., "US bank" hosted in unrelated jurisdiction) | -8 |
| Content | Password/payment form served over non-HTTPS | -20 |
| Content | Urgency/pressure language ("act now", "account suspended", "verify immediately") combined with a login form | -10 |
| Content | Excessive redirect chain (>3 hops) or redirect to different domain than entered | -12 |
| Brand impersonation | Domain is a close typosquat of a top-200 brand (edit distance 1–2, or homoglyph swap) | -30 |
| Positive signal | Domain age > 2 years + valid EV/OV cert + zero blacklist hits | +5 bonus (cap total at 100) |

### Verdict bands
- **80–100 → Safe** (green)
- **50–79 → Caution** (yellow) — proceed carefully, list specific reasons
- **0–49 → High Risk** (red) — strong recommendation not to enter payment/personal info

### Important nuance to build in
- If **any** hard blacklist hit occurs (Safe Browsing or PhishTank), cap the verdict at "High Risk" regardless of other positive signals — don't let a good SSL cert offset an active phishing flag.
- Always show **why**, not just the number — this is what makes it useful, not just a black-box score. Every deduction should render as a plain-language bullet: e.g., "Domain registered 6 days ago — very new domains are frequently used for short-lived scam campaigns."

---

## 8. Phase-wise build plan

### Phase 0 — Validate & scope (1 day)
- Write a 1-page pitch (problem, who it's for, what it checks, why it's standalone) and get Suproc PM sign-off **before** heavy building — this is the step that was skipped last time.
- Confirm with PM: is a rule-based scorer acceptable, or do they expect ML/LLM-driven scoring? (Recommend rule-based for MVP — more defensible, cheaper, faster.)

### Phase 1 — Signal collectors (2–3 days)
Build each as an independent, testable async function with a consistent output contract:
```python
class SignalResult(BaseModel):
    signal_name: str
    passed: bool          # True = no red flag
    deduction: int         # points removed, 0 if passed
    detail: str             # human-readable explanation
    raw_data: dict | None   # for debugging/audit
```
Build in this order (easiest → hardest):
1. SSL/TLS check (pure Python, no external API)
2. WHOIS/RDAP domain age
3. DNS + hosting ASN/geo lookup
4. Google Safe Browsing lookup
5. VirusTotal lookup
6. PhishTank lookup
7. Content fetch + HTML heuristics (forms, redirects, urgency keywords)
8. Typosquat/brand-impersonation checker (build your top-200 brand list as a JSON file first)

Test each collector standalone against 5 known-good sites and 5 known-scam/test sites (see Phase 4) before wiring them together.

### Phase 2 — Orchestration + scoring engine (1–2 days)
- `asyncio.gather()` all collectors with a per-collector timeout (e.g., 8s) so one slow API doesn't block the whole scan — if a collector times out, mark it "unavailable" and exclude it from scoring rather than failing the whole request.
- Implement the weighted deduction scorer reading from a `weights.json` config.
- Implement the hard-cap rule for blacklist hits.
- Add the Groq LLM call at the very end, fed the structured findings, prompted strictly to *summarize, not to re-score*.

### Phase 3 — API layer (1 day)
- `POST /scan` — body: `{ "url": "..." }` → returns full JSON (score, verdict, signals[], summary).
- `GET /scan/{id}` — retrieve a cached past scan by ID (for shareable report links).
- Add SQLite caching keyed by normalized domain, 24h TTL, to stay within free API rate limits and make repeat demo queries instant.
- Add basic rate limiting (e.g., `slowapi`) — 10 scans/minute/IP — before making it public, to protect your free API quotas.

### Phase 4 — Test set & calibration (1 day, don't skip)
Build a labeled test set:
- 15–20 known-legitimate major sites (banks, e-commerce, gov sites).
- 15–20 known-scam/phishing examples — use PhishTank's public feed and OpenPhish's public feed for current live examples, **never fabricate or actively visit sketchy sites in a browser with saved credentials**.
- Run the pipeline against the full set, check false-positive/false-negative rate, tune weights in `weights.json` until legitimate sites reliably land "Safe" and known scams land "High Risk."
- Document this calibration process — it's evidence of rigor for the Suproc showcase.

### Phase 5 — Frontend (2 days)
- Single input field + "Scan" button.
- Results view: big score number + colored verdict badge, then an expandable list of every signal with pass/fail icon and the plain-English detail line, then the LLM summary paragraph at the top (most people read that first, details second).
- Shareable link (`/report/{id}`) so a result can be sent to someone else.
- Empty/loading/error states (scan in progress, API failure, invalid URL).

### Phase 6 — Deploy, document, and package for Suproc (1 day)
- Deploy backend (Render/Railway free tier) and frontend (Vercel).
- Write the GitHub README: problem, architecture diagram, how to run locally, API docs, calibration methodology, screenshots.
- Record a 2–3 minute demo video/GIF: scan a known-safe site, scan a known-risky one, show the breakdown.
- Prepare the Suproc Marketplace listing copy: what it does, who it's for, link to live demo, link to repo.

**Total estimated build time: ~9–11 focused days**, which is realistic for a solo build alongside your internship and coursework — plan it across 2–3 weeks with buffer, not back-to-back days.

---

## 9. Suggested repo structure

```
website-scam-risk-detector/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI app, routes
│   │   ├── collectors/
│   │   │   ├── ssl_check.py
│   │   │   ├── whois_check.py
│   │   │   ├── dns_hosting.py
│   │   │   ├── safe_browsing.py
│   │   │   ├── virustotal.py
│   │   │   ├── phishtank.py
│   │   │   ├── content_heuristics.py
│   │   │   └── typosquat.py
│   │   ├── scoring/
│   │   │   ├── weights.json
│   │   │   └── engine.py
│   │   ├── llm/
│   │   │   └── summarizer.py       # Groq call, summary-only
│   │   ├── cache/
│   │   │   └── db.py               # SQLite cache
│   │   └── models.py               # Pydantic schemas
│   ├── data/
│   │   └── top_brands.json         # for typosquat checks
│   ├── tests/
│   │   └── test_labeled_set.py     # Phase 4 calibration test
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/index.tsx
│   │   ├── pages/report/[id].tsx
│   │   └── components/ScoreCard.tsx, SignalList.tsx
│   └── package.json
├── docs/
│   ├── architecture.md
│   └── calibration-results.md
└── README.md
```

---

## 10. Risks / things to get right

- **API rate limits will bite you in a live public demo** — caching is not optional, build it in Phase 3, not as an afterthought.
- **Don't let the LLM touch the score.** Keep it strictly summary-only, or you lose the "auditable, deterministic" trust story that differentiates this from "just asking an LLM if a site looks scammy."
- **False positives on new-but-legitimate sites** (e.g., a startup's brand-new site) are the main failure mode — the "Caution" band exists specifically to avoid over-confidently calling something a scam just because it's young; lean on combining signals, not domain age alone.
- **Never actively interact with live phishing sites** (don't submit test credentials, don't click through to payment pages) — passive fetching (HTML/headers) is fine and sufficient for the content heuristics.
- **Respect API terms of service** for each provider (Safe Browsing, VirusTotal, PhishTank) — read the usage policy for the free tier before going live publicly.

---

## 11. Next step

Before Phase 1: write the 1-page pitch from Phase 0 and get it in front of Suproc's PM. Once approved, come back and this guide gives you everything needed to execute Phases 1–6 end-to-end.
