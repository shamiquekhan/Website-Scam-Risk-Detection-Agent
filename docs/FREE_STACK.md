# Why Every Tool Here Is Free ($0 Build & Run)

ScamShield AI runs with **zero paid services and zero API keys required**. Every
dependency below was chosen because it is free, open-source, or has a generous
free tier that never gates the core scan path.

## The zero-cost signal stack

| Signal | Data source | Key required? | Notes |
|--------|-------------|---------------|-------|
| SSL/TLS certificate | Python `ssl` (direct socket) | No | On-device TLS handshake |
| Domain age | IANA RDAP bootstrap + `rdap.org` | No | Keyless, routed to authoritative registries |
| DNS + hosting ASN/geo | `dns.resolver` + `ip-api.com` + `ipwho.is` | No | Both geo lookups are keyless |
| URLhaus blocklist | `https://urlhaus.abuse.ch/downloads/text_online/` | No | Public download, refreshed daily |
| OpenPhish feed | `https://openphish.com/feed.txt` | No | Public feed, refreshed every 6h |
| Local ML classifier | ONNX model trained in-repo | No | Runs on-device, no API call |
| URL structure heuristics | In-repo deterministic rules | No | Always available |
| Content heuristics | `httpx` + `BeautifulSoup` | No | Fetches the page directly |
| Typosquat check | Local `top_brands.json` + Levenshtein | No | On-device |
| LLM summary | **Ollama** (local, e.g. Phi-3 Mini) | No | On-device, zero latency |
| LLM fallback | Groq free tier | Optional | 1M tokens/day, non-gating |

## Paid dependencies replaced

| Original (paid/limited) | Free replacement | Why it works |
|--------------------------|------------------|--------------|
| Google Safe Browsing API (key, non-commercial) | OpenPhish free feed + local ML | Feed updates every 6h; ML flags structural phishing |
| VirusTotal (4 req/min) | URLhaus blocklist + local ML | URLhaus is unauthenticated; ML is on-device |
| IPinfo token | `ip-api.com` + `ipwho.is` | Both keyless, generous limits |
| Groq (external) | Ollama local LLM | Runs entirely on-device |
| URLhaus auth key | URLhaus public blocklist download | The `text_online` dump needs no key |

## What is optional

Everything in the table below is **optional**. Each collector degrades
gracefully to `available: false` when its (optional) key is absent, and the
scoring engine is fail-closed: too many missing signals yields
**Insufficient Data**, never a false-clean verdict.

| Env var | Purpose |
|---------|---------|
| `VIRUSTOTAL_API_KEY` | Adds a VirusTotal reputation signal |
| `GOOGLE_SAFE_BROWSING_API_KEY` | Adds the Safe Browsing signal (OpenPhish is the keyless default) |
| `URLHAUS_AUTH_KEY` | Upgrades URLhaus to the authenticated API (blocklist is default) |
| `IPINFO_TOKEN` | Upgrades geo lookup to IPinfo (keyless fallbacks exist) |
| `GROQ_API_KEY` | Second LLM summarizer fallback (Ollama is default) |

## Deployment free tiers

| Service | Free tier | Use |
|---------|-----------|-----|
| Vercel | Hobby (unlimited) | Next.js frontend |
| Render | 750 hrs/month | FastAPI backend |
| GitHub Actions | 2,000 min/month | CI/CD |
| Docker Hub | Unlimited public images | Ollama + backend images |
| SQLite | Built-in | 24h scan cache |

No credit card is needed to build, run, or deploy this agent.