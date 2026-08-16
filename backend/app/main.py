from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.models import ScanRequest, ScanResult, BatchScanRequest, BatchScanResult
from app.orchestrator import run_scan, run_scan_limited
from app.utils import normalize_url

app = FastAPI(title="ScamShield AI - Website Scam Risk Detector", version="2.0.0")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/scan", response_model=ScanResult)
@limiter.limit("10/minute")
async def scan(request: Request, scan_req: ScanRequest):
    try:
        normalized = normalize_url(scan_req.url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    result = await run_scan(scan_req.url)
    return result


@app.post("/scan/batch", response_model=BatchScanResult)
@limiter.limit("5/minute")
async def batch_scan(request: Request, batch_req: BatchScanRequest):
    if not batch_req.urls:
        raise HTTPException(status_code=422, detail="urls must not be empty")
    if len(batch_req.urls) > 100:
        raise HTTPException(status_code=422, detail="Maximum 100 URLs per batch")
    for url in batch_req.urls:
        try:
            normalize_url(url)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"Invalid URL '{url}': {e}")

    results, errors = await run_scan_limited(batch_req.urls, batch_req.max_concurrency)
    return BatchScanResult(
        results=[r for r in results if r is not None],
        scanned=len(results) - len(errors),
        failed=len(errors),
        errors=errors,
    )


@app.get("/scan/{scan_id}", response_model=ScanResult)
async def get_scan(scan_id: str):
    from app.cache.db import _get_connection
    conn = await _get_connection()
    try:
        cursor = await conn.execute(
            "SELECT result_json FROM scans WHERE scan_id = ?", (scan_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Scan not found")
        import json
        from app.models import SignalResult
        data = json.loads(row[0])
        signals = [SignalResult(**s) for s in data["signals"]]
        return ScanResult(**{**data, "signals": signals, "cached": True})
    finally:
        await conn.close()
