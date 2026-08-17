from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Optional


def to_dict(obj: Any) -> dict[str, Any]:
    """Convert a dataclass (or nested dataclass) tree to a JSON-safe dict."""
    return _to_json_safe(asdict(obj))


def _to_json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _to_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_json_safe(v) for v in value]
    return value


@dataclass
class SignalResult:
    signal_name: str
    category: str
    passed: bool
    deduction: int
    detail: str
    raw_data: Optional[dict[str, Any]] = None
    available: bool = True
    availability_reason: Optional[str] = None


@dataclass
class ScanRequest:
    url: str


@dataclass
class BatchScanRequest:
    urls: list[str]
    max_concurrency: Optional[int] = 4


@dataclass
class ScanResult:
    scan_id: str
    url: str
    normalized_domain: str
    verdict: str
    summary: str
    signals: list[SignalResult]
    scanned_at: datetime
    score: Optional[int] = None
    completed_signals: int = 0
    total_signals: int = 0
    confidence: int = 0
    cached: bool = False


@dataclass
class BatchScanResult:
    results: list[ScanResult]
    scanned: int
    failed: int
    errors: list[dict[str, str]]