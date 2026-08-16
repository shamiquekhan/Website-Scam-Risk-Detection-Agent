# SKILLS.md

Catalog of the distinct capabilities ("skills") this system has, what each one does, what it depends on, and how confident/fast it is. Useful both as internal documentation and as the basis for the Marketplace listing copy (which skills = which selling points).

A "skill" here is a self-contained capability the backend can perform - mostly 1:1 with a collector, but a couple are cross-cutting.

---

## 1. Domain age & trust check
- **What it does:** Determines when a domain was registered and by whom (where not privacy-masked), via RDAP/WHOIS.
- **Why it matters:** Scam sites overwhelmingly use domains registered days or weeks before the campaign; legitimate businesses' domains are typically old.
- **Confidence:** High for age itself (RDAP data is authoritative). Registrant identity is often masked by privacy services, which is normal for legitimate sites too - treated as a weak signal, not scored heavily alone.
- **Speed:** Fast (~200-500ms, single RDAP call, no key required).
- **Dependency:** `rdap.org`, fallback `python-whois`.

## 2. SSL/TLS certificate check
- **What it does:** Verifies HTTPS availability, certificate validity, expiry, and hostname match.
- **Why it matters:** No HTTPS or an invalid cert on a page requesting payment/login info is a strong, cheap-to-check red flag.
- **Confidence:** Very high - this is a direct cryptographic check, not a third-party opinion.
- **Speed:** Fast (~100-300ms, direct socket connection, no external API/key).
- **Dependency:** None external - pure Python `ssl`/`socket`.

## 3. Multi-source reputation/blacklist check
- **What it does:** Cross-references the URL against Google Safe Browsing, VirusTotal (60+ engines), and URLhaus.
- **Why it matters:** These are the highest-confidence signals available - a confirmed blacklist hit means someone has already verified this specific URL is malicious.
- **Confidence:** Very high when a hit occurs (near-zero false positive rate on confirmed hits). Absence of a hit does **not** mean safe - very new scam sites may not be indexed yet.
- **Speed:** Moderate (~1-3s combined, network-bound; VirusTotal is the slowest and most rate-limited).
- **Dependency:** Google Safe Browsing API key, VirusTotal API key, URLhaus auth key.

## 4. Hosting/infrastructure analysis
- **What it does:** Resolves DNS, identifies hosting ASN/organization/country, flags known high-abuse hosting.
- **Why it matters:** Scam operations cluster on specific cheap/anonymous hosting providers; a mismatch between claimed business location and hosting country is a secondary red flag.
- **Confidence:** Moderate - this is a correlational signal, not direct proof, so it's weighted lightly and used to corroborate other signals rather than decide the verdict alone.
- **Speed:** Fast (~300-500ms).
- **Dependency:** `dnspython`, ipinfo.io free tier.

## 5. Content/behavior heuristics
- **What it does:** Inspects the live page for password forms on non-HTTPS, cross-domain redirect chains, and urgency/pressure language combined with a form.
- **Why it matters:** Catches scam patterns even on brand-new domains with no reputation history yet.
- **Confidence:** Moderate - heuristic-based, deliberately conservative (only deducts on *combinations* of signals, e.g. urgency language + form present, not on either alone) to avoid false-positiving legitimate security/login pages.
- **Speed:** Slowest of the collectors (~1-4s, depends on target site's response time and page weight).
- **Dependency:** `httpx`, `BeautifulSoup`, no external API.

## 6. Brand impersonation / typosquat detection
- **What it does:** Compares the scanned domain against a curated list of major brands using edit distance and homoglyph pattern matching.
- **Why it matters:** This is the system's most distinctive capability - catches the "looks almost exactly like PayPal" pattern that pure reputation/blacklist checks miss entirely for a brand-new impersonation domain with zero history.
- **Confidence:** High on exact typosquat patterns, moderate on more creative impersonations (e.g., unrelated-looking domains with a PayPal-branded page) - the latter would need the content-heuristics or visual-similarity skill (V2) to catch.
- **Speed:** Fast (~50-100ms, pure string comparison against a local list).
- **Dependency:** None external - local `top_brands.json`, `rapidfuzz`.

## 7. Deterministic risk scoring
- **What it does:** Combines all available signals into a single explainable 0-100 score and Safe/Caution/High-Risk verdict via a weighted deduction model with a hard-cap rule for confirmed blacklist hits.
- **Why it matters:** This is what makes the tool trustworthy rather than a black box - every point deducted traces to a named, inspectable reason.
- **Confidence:** As strong as its inputs and calibration (see `docs/calibration-results.md`); this skill's own logic is fully deterministic and unit-tested.
- **Speed:** Instant (in-memory computation, no I/O).

## 8. Plain-English risk summary generation
- **What it does:** Takes the structured, already-scored findings and writes 2-4 sentences a non-technical person can act on.
- **Why it matters:** Most users will read the summary and glance at the badge, not the raw signal list - this is the primary UX surface.
- **Confidence:** High for faithfulness to the underlying data (prompt strictly forbids inventing findings or changing the verdict); treat any observed drift as a bug to fix in the prompt, not the model.
- **Speed:** ~1-2s (Groq inference, small/fast model).
- **Dependency:** Groq API key.

## 9. Result caching & rate-limit protection
- **What it does:** Caches scan results per normalized domain for 24h, rate-limits scan requests per IP.
- **Why it matters:** Keeps the public demo usable within free-tier API quotas and gives near-instant repeat lookups.
- **Confidence:** N/A (infrastructure, not a detection skill).
- **Speed:** Cache hit ~5-10ms vs. a full scan's several seconds.
- **Dependency:** SQLite, `slowapi`.

---

## Skills explicitly not yet built (V2 candidates)

- Visual similarity detection (screenshot comparison against known brand login pages)
- Historical trend tracking (has this domain's score changed over time)
- Community/report-based corroboration (e.g., scraping public scam-report databases via Apify)
- Bulk/batch scanning skill

These are documented so it's clear what "not built yet" looks like versus "considered and rejected" - none have been rejected, they're simply out of MVP scope per `docs/build-guide.md`.
