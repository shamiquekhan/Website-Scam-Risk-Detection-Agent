from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class SignalResult(BaseModel):
    signal_name: str
    category: str
    passed: bool
    deduction: int
    detail: str
    raw_data: Optional[dict[str, Any]] = None
    available: bool = True
    availability_reason: Optional[str] = None


class ScanRequest(BaseModel):
    url: str


class BatchScanRequest(BaseModel):
    urls: list[str]
    max_concurrency: Optional[int] = 4


class ScanResult(BaseModel):
    scan_id: str
    url: str
    normalized_domain: str
    score: Optional[int] = None
    verdict: str
    summary: str
    signals: list[SignalResult]
    scanned_at: datetime
    completed_signals: int = 0
    total_signals: int = 0
    confidence: int = 0
    cached: bool = False


class BatchScanResult(BaseModel):
    results: list[ScanResult]
    scanned: int
    failed: int
    errors: list[dict[str, str]]
