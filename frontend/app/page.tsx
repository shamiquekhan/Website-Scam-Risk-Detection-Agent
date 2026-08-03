'use client'

import { useState } from 'react'
import ScoreCard from '@/components/ScoreCard'
import SignalList from '@/components/SignalList'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface ScanResult {
  scan_id: string
  url: string
  score: number | null
  verdict: string
  summary: string
  signals: any[]
  cached: boolean
  scanned_at: string
  completed_signals: number
  total_signals: number
  confidence: number
}

export default function Home() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ScanResult | null>(null)
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    setResult(null)

    try {
      const res = await fetch(`${API_URL}/scan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Scan failed')
      }
      const data = await res.json()
      setResult(data)
    } catch (err: any) {
      setError(err.message || 'Could not connect to scanner')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">
        Website Scam Risk Detector
      </h1>
      <p className="text-gray-600 mb-6">
        Enter a URL to check if it is safe or a scam. Results include a risk score, verdict, and detailed signal breakdown.
      </p>

      <form onSubmit={handleSubmit} className="mb-8">
        <div className="flex gap-2">
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com"
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !url.trim()}
            className="px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Scanning...' : 'Scan'}
          </button>
        </div>
      </form>

      {loading && (
        <div className="text-center py-8">
          <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-3" />
          <p className="text-gray-500">Scanning website... this takes a few seconds.</p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 mb-6">
          {error}
        </div>
      )}

      {result && (
        <div>
          <ScoreCard
            score={result.score}
            verdict={result.verdict}
            summary={result.summary}
            completedSignals={result.completed_signals}
            totalSignals={result.total_signals}
            confidence={result.confidence}
          />
          <SignalList signals={result.signals} />
          <p className="text-xs text-gray-400 mt-4 text-center">
            Scanned at {new Date(result.scanned_at).toLocaleString()}
            {result.cached ? ' (cached result)' : ''}
          </p>
        </div>
      )}
    </main>
  )
}
