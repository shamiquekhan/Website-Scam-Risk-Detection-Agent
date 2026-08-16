'use client'

import { useState } from 'react'
import Link from 'next/link'
import ScoreCard from '@/components/ScoreCard'
import SignalList from '@/components/SignalList'
import LoadingSkeleton from '@/components/LoadingSkeleton'
import { scanUrl, ScanResult } from '@/lib/api'

const CHECKS = [
  'SSL Certificate',
  'Domain Age & WHOIS',
  'DNS & Hosting',
  'Threat Intelligence',
  'Local ML Classifier',
  'URL Structure',
  'Page Content',
  'Brand Impersonation',
]

export default function Home() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ScanResult | null>(null)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    setResult(null)

    try {
      const data = await scanUrl(url)
      setResult(data)
    } catch (err: any) {
      setError(err.message || 'Could not connect to scanner')
    } finally {
      setLoading(false)
    }
  }

  async function copyReportLink() {
    if (!result) return
    const link = `${window.location.origin}/report/${result.scan_id}`
    try {
      await navigator.clipboard.writeText(link)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      window.prompt('Copy this report link:', link)
    }
  }

  return (
    <main className="max-w-2xl mx-auto px-4 py-10">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">ScamShield AI</h1>
        <p className="text-slate-400">
          Zero-cost website scam & phishing risk detector — 11 independent checks, local ML,
          no API keys required.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="mb-8">
        <div className="flex flex-col sm:flex-row gap-2">
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com"
            className="flex-1 px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !url.trim()}
            className="px-6 py-3 bg-cyan-600 text-white font-medium rounded-lg hover:bg-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Scanning…' : 'Scan'}
          </button>
        </div>
        <p className="text-xs text-slate-500 mt-2 text-center sm:text-left">
          {result?.cached ? 'Cached result (scanned within the last 24h). ' : ''}
          <Link href="/batch" className="text-cyan-400 hover:underline">
            Bulk-scan many URLs →
          </Link>
        </p>
      </form>

      {loading && <LoadingSkeleton checks={CHECKS} />}

      {error && (
        <div className="bg-red-950/50 border border-red-800 text-red-300 rounded-xl p-4 mb-6 animate-fade-up">
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
          <div className="mt-5 flex flex-col sm:flex-row items-center justify-between gap-3">
            <p className="text-xs text-slate-500">
              Scanned at {new Date(result.scanned_at).toLocaleString()}
              {result.cached ? ' (cached result)' : ''}
            </p>
            <button
              type="button"
              onClick={copyReportLink}
              className="px-4 py-2 text-sm bg-slate-800 border border-slate-700 rounded-lg text-slate-200 hover:bg-slate-700 transition-colors"
            >
              {copied ? 'Copied ✓' : 'Copy shareable report link'}
            </button>
          </div>
        </div>
      )}
    </main>
  )
}