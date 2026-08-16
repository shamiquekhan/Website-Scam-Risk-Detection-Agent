export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface SignalResult {
  signal_name: string
  category: string
  passed: boolean
  deduction: number
  detail: string
  raw_data?: Record<string, unknown> | null
  available: boolean
  availability_reason?: string | null
}

export interface ScanResult {
  scan_id: string
  url: string
  normalized_domain: string
  score: number | null
  verdict: string
  summary: string
  signals: SignalResult[]
  scanned_at: string
  completed_signals: number
  total_signals: number
  confidence: number
  cached: boolean
}

export async function scanUrl(url: string): Promise<ScanResult> {
  const res = await fetch(`${API_URL}/scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Scan failed')
  }
  return res.json()
}

export async function scanBatch(urls: string[]): Promise<{
  results: ScanResult[]
  scanned: number
  failed: number
  errors: { url: string; error: string }[]
}> {
  const res = await fetch(`${API_URL}/scan/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ urls }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Batch scan failed')
  }
  return res.json()
}