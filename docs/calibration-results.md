# Calibration Results

Status: **PENDING — live calibration not yet run.**

## Methodology

The scoring engine is calibrated against two labeled sets before the tool can claim reliable verdicts:

- **Known-good set** (15–20 URLs): major banks, e-commerce, government, established SaaS.
- **Known-bad set** (15–20 URLs): currently-live phishing URLs pulled from URLhaus / OpenPhish public feeds **at test-run time** (phishing URLs get taken down fast, so fixtures must be fetched dynamically, never hardcoded).

For each set we run the full pipeline and assert:

- Known-good **average score ≥ 80** (target: Safe).
- Known-bad **average score ≤ 49** (target: High Risk).
- Per-URL results recorded in a markdown table for inspection.

Failures are investigated, weights in `backend/app/scoring/weights.json` are tuned, and the suite is re-run until the false-positive/false-negative rate is acceptable. The final numbers are recorded below as evidence of rigor.

## Rules observed during calibration

- Never actively interact with live phishing sites (no form submissions, no credentials, no following payment flows) — passive fetching only.
- Respect API terms of service and free-tier rate limits for Safe Browsing, VirusTotal, and URLhaus.
- Any change to `scoring/engine.py` or `weights.json` requires re-running calibration and updating this file before the change is considered done.

## Results table

_To be populated after the calibration suite is run with live API keys configured._

| URL | Score | Verdict | Notes |
|---|---|---|---|
| — | — | — | pending |

## How to run

```bash
cd backend && source venv/bin/activate
pytest tests/test_labeled_set.py -v   # slow — hits live APIs
```
