import asyncio
import uuid
from datetime import datetime, timezone
from app.models import SignalResult, ScanResult
from app.utils import normalize_url, extract_domain
from app.scoring.engine import calculate_assessment
from app.llm.summarizer import summarize
from app.cache.db import get_cached, save_scan
from app.collectors import (
    ssl_check,
    whois_check,
    dns_hosting,
    safe_browsing,
    virustotal,
    urlhaus,
    content_heuristics,
    typosquat,
)

COLLECTOR_TIMEOUT = 8

COLLECTORS = [
    ("ssl_check", ssl_check.check),
    ("whois_check", whois_check.check),
    ("dns_hosting", dns_hosting.check),
    ("safe_browsing", safe_browsing.check),
    ("virustotal", virustotal.check),
    ("urlhaus", urlhaus.check),
    ("content_heuristics", content_heuristics.check),
    ("typosquat", typosquat.check),
]


async def run_scan(url: str) -> ScanResult:
    normalized_url = normalize_url(url)
    domain = extract_domain(normalized_url)

    cached = await get_cached(domain)
    if cached is not None:
        return cached

    async def run_collector(name: str, coro):
        try:
            return await asyncio.wait_for(coro, timeout=COLLECTOR_TIMEOUT)
        except Exception:
            return SignalResult(
                signal_name=name,
                category="unknown",
                passed=True,
                deduction=0,
                detail=f"{name} check timed out or failed.",
                available=False,
                availability_reason="error",
            )

    tasks = [run_collector(name, collector(normalized_url)) for name, collector in COLLECTORS]
    results = await asyncio.gather(*tasks)

    score, verdict, completed_signals, total_signals, confidence = calculate_assessment(results)

    scan_result = ScanResult(
        scan_id=str(uuid.uuid4()),
        url=normalized_url,
        normalized_domain=domain,
        score=score,
        verdict=verdict,
        summary="",
        signals=results,
        scanned_at=datetime.now(timezone.utc),
        completed_signals=completed_signals,
        total_signals=total_signals,
        confidence=confidence,
        cached=False,
    )

    summary_text = await summarize(scan_result)
    scan_result.summary = summary_text

    if scan_result.score is not None:
        await save_scan(scan_result)

    return scan_result
