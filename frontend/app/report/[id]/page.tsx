'use client'

import { useEffect, useState } from 'react'
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

export default function ReportPage({ params }: { params: { id: string } }) {
  const [result, setResult] = useState<ScanResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function fetchReport() {
      try {
        const res = await fetch(`${API_URL}/scan/${params.id}`)
        if (!res.ok) throw new Error('Report not found')
        const data = await res.json()
        setResult(data)
      } catch (err: any) {
        setError(err.message || 'Could not load report')
      } finally {
        setLoading(false)
      }
    }
    fetchReport()
  }, [params.id])

  if (loading) {
    return (
      <main className="max-w-2xl mx-auto px-4 py-8 text-center">
        <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-3" />
        <p className="text-gray-500">Loading report...</p>
      </main>
    )
  }

  if (error) {
    return (
      <main className="max-w-2xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4">
          {error}
        </div>
      </main>
    )
  }

  if (!result) return null

  return (
    <main className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Scan Report</h1>
      <p className="text-sm text-gray-500 mb-6">URL: {result.url}</p>
      <ScoreCard
        score={result.score}
        verdict={result.verdict}
        summary={result.summary}
        completedSignals={result.completed_signals}
        totalSignals={result.total_signals}
        confidence={result.confidence}
      />
      <SignalList signals={result.signals} />
    </main>
  )
}
