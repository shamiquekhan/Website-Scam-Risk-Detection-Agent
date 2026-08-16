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

Status: **PARTIAL — deterministic + local-ML signals calibrated; live-reputation
signals still require optional API keys.**

The checks below ran with only the free/keyless signal stack (OpenPhish, URLhaus
blocklist, local ML, URL structure, SSL, DNS, content, typosquat) and no API keys.
Results are from a live run against the full 11-signal pipeline (external network
signals varied run-to-run).

| URL | Score | Verdict | Notes |
|---|---|---|---|
| https://example.com/ | 73–82 | Likely Safe | Established domain, valid SSL, all reputation feeds clean |
| https://github.com/ | 80+ | Likely Safe | Not tainted by URLhaus `github.com/user/...` malware reports (path-aware matching) |
| https://fidelity-investment.vercel.app/ | 18 | High Risk | OpenPhish feed hit (−40) + local ML 98% (−30) |
| https://secure-login-paypal-account.tk/login | 6 | High Risk | Local ML 99%, suspicious TLD, no HTTPS |

## Local ML model (holdout evaluation)

Trained on OpenPhish positives + synthetic phishing variants + Majestic Million
negatives (10,100 samples, Random Forest, 200 trees).

| Metric | Value |
|--------|-------|
| Precision (phishing) | **0.919** |
| Recall (phishing) | **0.867** |
| F1 | **0.892** |
| Confusion matrix | TN 1568 / FP 32 / FN 56 / TP 364 |

Sample inferences on the bundled ONNX model: `github.com` → 0.02, `google.com` →
0.01, real OpenPhish entry → 0.98, `secure-login-paypal-account.tk` → 0.99.

## How to run

```bash
cd backend && source venv/bin/activate
pytest tests/test_labeled_set.py -v   # slow — hits live APIs
```
