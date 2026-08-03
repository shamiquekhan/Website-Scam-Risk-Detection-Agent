import aiosqlite
import json
from datetime import datetime, timezone, timedelta
from typing import Optional
from app.models import ScanResult, SignalResult

DB_PATH = "cache.db"


async def _get_connection() -> aiosqlite.Connection:
    conn = await aiosqlite.connect(DB_PATH)
    await conn.execute(
        "CREATE TABLE IF NOT EXISTS scans ("
        "scan_id TEXT PRIMARY KEY, "
        "domain TEXT, "
        "result_json TEXT, "
        "created_at TIMESTAMP"
        ")"
    )
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_domain ON scans(domain)")
    await conn.commit()
    return conn


async def get_cached(domain: str) -> Optional[ScanResult]:
    conn = await _get_connection()
    try:
        cursor = await conn.execute(
            "SELECT result_json, created_at FROM scans WHERE domain = ? ORDER BY created_at DESC LIMIT 1",
            (domain,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        created_at = datetime.fromisoformat(row[1])
        if datetime.now(timezone.utc) - created_at > timedelta(hours=24):
            return None
        data = json.loads(row[0])
        if not data.get("total_signals"):
            return None
        signals = [SignalResult(**s) for s in data["signals"]]
        return ScanResult(**{**data, "signals": signals, "cached": True})
    finally:
        await conn.close()


async def save_scan(result: ScanResult) -> None:
    conn = await _get_connection()
    try:
        data = result.model_dump(mode="json")
        data["signals"] = [s.model_dump(mode="json") for s in result.signals]
        await conn.execute(
            "INSERT OR REPLACE INTO scans (scan_id, domain, result_json, created_at) VALUES (?, ?, ?, ?)",
            (result.scan_id, result.normalized_domain, json.dumps(data), result.scanned_at.isoformat()),
        )
        await conn.commit()
    finally:
        await conn.close()
