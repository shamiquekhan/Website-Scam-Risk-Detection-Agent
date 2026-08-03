# TOOLS.md

Reference for every external tool/API and key internal library this system depends on: what it's used for, auth requirements, rate limits, and fallback behavior if it's unavailable.

---

## External APIs

### Google Safe Browsing API
- **Used in:** `collectors/safe_browsing.py`
- **Purpose:** Checks URL against Google's malware/phishing/unwanted-software blacklists.
- **Auth:** API key (Google Cloud Console, free to enable).
- **Rate limit:** Generous free quota (thousands/day) — not a practical bottleneck for MVP traffic.
- **Fallback if unavailable:** Mark signal `available=False`, exclude from scoring, note in response that this check couldn't be completed.
- **Docs:** `developers.google.com/safe-browsing`

### VirusTotal API v3
- **Used in:** `collectors/virustotal.py`
- **Purpose:** Aggregates verdicts from 60+ antivirus/security engines for a given URL.
- **Auth:** API key (free account).
- **Rate limit:** **4 requests/minute, 500/day on free tier** — the tightest constraint in the system. Cache aggressively; consider a small internal queue/delay if running the calibration suite (40 URLs) in one pass.
- **Fallback if unavailable:** Mark `available=False`, exclude from scoring.
- **Docs:** `developers.virustotal.com`

### URLhaus (abuse.ch)
- **Used in:** `collectors/urlhaus.py`
- **Purpose:** Checks URL against the URLhaus malware/phishing URL database.
- **Auth:** `Auth-Key` header from an abuse.ch account (auth.abuse.ch).
- **Rate limit:** Free community tier; treat as generous but not unlimited.
- **Fallback if unavailable:** Mark `available=False`, exclude from scoring.
- **Docs:** `urlhaus.abuse.ch/api`

### RDAP (`rdap.org`) / WHOIS fallback
- **Used in:** `collectors/whois_check.py`
- **Purpose:** Domain registration date, registrar, registrant privacy status.
- **Auth:** None required for RDAP.
- **Rate limit:** No published hard limit for reasonable use; be a good citizen, don't hammer it in tests.
- **Fallback:** If RDAP has no record for a TLD, fall back to `python-whois` library (parses raw WHOIS text, less structured/reliable).

### ipinfo.io
- **Used in:** `collectors/dns_hosting.py`
- **Purpose:** IP → ASN, hosting organization, country lookup.
- **Auth:** Free API token.
- **Rate limit:** 50,000 requests/month free tier — comfortable for MVP scale with caching.
- **Fallback if unavailable:** Falls back to ip-api.com (keyless, ~45 req/min); if both fail, mark `available=False`.

### ip-api.com
- **Used in:** `collectors/dns_hosting.py` (fallback)
- **Purpose:** IP → ASN, hosting organization, country lookup.
- **Auth:** None (non-commercial use).
- **Rate limit:** ~45 requests/minute.
- **Fallback if unavailable:** Mark `available=False`, exclude from scoring.

### Groq API
- **Used in:** `llm/summarizer.py`
- **Purpose:** Generates the plain-English summary paragraph only. **Never used for scoring.**
- **Auth:** API key.
- **Rate limit:** Check current free-tier limits at time of build (changes periodically) — cache the summary alongside the rest of the scan result so repeat lookups don't re-call it.
- **Fallback if unavailable:** Fall back to a templated string summary built from the structured signal list (e.g., "This site received a score of X due to: [list of failed signal details]").

---

## Internal libraries

| Library | Used for | Notes |
|---|---|---|
| `fastapi` | Web framework | Async-native |
| `httpx` | Async HTTP client | Used for all outbound API calls and page fetches |
| `dnspython` | DNS resolution | Used in hosting check |
| `python-whois` | WHOIS fallback | Only invoked when RDAP has no data |
| `tldextract` | Domain parsing | Correctly splits subdomain/registrable domain/TLD, including multi-part TLDs like `.co.uk` |
| `beautifulsoup4` | HTML parsing | Content heuristics collector |
| `python-Levenshtein` | Edit-distance calc | Typosquat detection |
| `groq` | Groq SDK | Summarizer only |
| `aiosqlite` | Async SQLite | Cache layer |
| `slowapi` | Rate limiting | Per-IP limit on `/scan` |
| `pydantic` | Data validation/schemas | Every cross-boundary data structure |
| `pytest` / `pytest-asyncio` | Testing | Unit tests + calibration suite |

---

## Data files (not APIs, but tool-like local resources)

| File | Purpose | Maintenance |
|---|---|---|
| `backend/data/top_brands.json` | Reference list for typosquat detection | Start at ~40–50 major brands, expand over time; adding a brand is a config change, not a code change |
| `backend/data/high_risk_asn.json` | Known high-abuse hosting ASNs | Seed manually from public writeups; expect to revisit periodically, this list goes stale |
| `backend/app/scoring/weights.json` | All scoring deduction values | The single place to tune scoring behavior; changes require re-running the calibration suite |

---

## Tool-availability degradation policy

The system is designed so that **no single external tool being down takes the whole scan down**. If a collector's `available=False`:
- It's excluded from both the score sum and the hard-cap check.
- The frontend shows it as "Check unavailable" rather than a pass or fail.
- If *most* signals are unavailable (e.g., 5+ of 8), the API should still return a result but the frontend should visibly flag "Limited data — verdict confidence reduced" rather than presenting a full-confidence badge on a mostly-empty signal set. (Implement this threshold check in `orchestrator.py` when building section 6 of `docs/implementation-plan.md`.)
