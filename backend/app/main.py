from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.models import ScanRequest, ScanResult
from app.orchestrator import run_scan
from app.utils import normalize_url

app = FastAPI(title="Website Scam Risk Detector", version="1.0.0")

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
