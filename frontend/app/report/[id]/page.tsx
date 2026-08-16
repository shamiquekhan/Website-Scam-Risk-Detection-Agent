'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import ScoreCard from '@/components/ScoreCard'
import SignalList from '@/components/SignalList'
import { API_URL, ScanResult } from '@/lib/api'

export default function ReportPage({ params }: { params: { id: string } }) {
  const [result, setResult] = useState<ScanResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)

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

  async function copyReportLink() {
    const link = window.location.href
    try {
      await navigator.clipboard.writeText(link)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      window.prompt('Copy this report link:', link)
    }
  }

  if (loading) {
    return (
      <main className="max-w-2xl mx-auto px-4 py-10 text-center">
        <div className="animate-spin h-8 w-8 border-2 border-cyan-500 border-t-transparent rounded-full mx-auto mb-3" />
        <p className="text-slate-400">Loading report…</p>
      </main>
    )
  }

  if (error) {
    return (
      <main className="max-w-2xl mx-auto px-4 py-10">
        <div className="bg-red-950/50 border border-red-800 text-red-300 rounded-xl p-4">{error}</div>
        <Link href="/" className="text-cyan-400 hover:underline text-sm mt-4 inline-block">
          ← Back to scanner
        </Link>
      </main>
    )
  }

  if (!result) return null

  return (
    <main className="max-w-2xl mx-auto px-4 py-10">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">Scan Report</h1>
        <Link href="/" className="text-sm text-cyan-400 hover:underline">
          ← New scan
        </Link>
      </div>
      <p className="text-sm text-slate-400 mb-6 break-all">URL: {result.url}</p>
      <ScoreCard
        score={result.score}
        verdict={result.verdict}
        summary={result.summary}
        completedSignals={result.completed_signals}
        totalSignals={result.total_signals}
        confidence={result.confidence}
      />
      <SignalList signals={result.signals} />
      <div className="mt-5 flex flex-col sm:flex-row items-center justify-between gap-3">
        <p className="text-xs text-slate-500">
          Report ID: {result.scan_id} · Scanned {new Date(result.scanned_at).toLocaleString()}
        </p>
        <button
          type="button"
          onClick={copyReportLink}
          className="px-4 py-2 text-sm bg-slate-800 border border-slate-700 rounded-lg text-slate-200 hover:bg-slate-700 transition-colors"
        >
          {copied ? 'Copied ✓' : 'Copy report link'}
        </button>
      </div>
    </main>
  )
}