'use client'

import { useState } from 'react'
import Link from 'next/link'
import { scanBatch, ScanResult } from '@/lib/api'
import { verdictStyle, signalTone, SIGNAL_LABELS } from '@/lib/verdicts'

export default function BatchPage() {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<ScanResult[]>([])
  const [errors, setErrors] = useState<{ url: string; error: string }[]>([])
  const [error, setError] = useState('')

  const urls = text
    .split(/\r?\n|,/)
    .map((line) => line.trim())
    .filter(Boolean)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (urls.length === 0) return
    setLoading(true)
    setError('')
    setResults([])
    setErrors([])

    try {
      const data = await scanBatch(urls.slice(0, 100))
      setResults(data.results)
      setErrors(data.errors)
    } catch (err: any) {
      setError(err.message || 'Batch scan failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="max-w-3xl mx-auto px-4 py-10">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">Bulk Scan</h1>
        <Link href="/" className="text-sm text-cyan-400 hover:underline">
          ← Single scan
        </Link>
      </div>

      <form onSubmit={handleSubmit} className="mb-6">
        <label className="block text-sm text-slate-300 mb-2">
          Paste up to 100 URLs (one per line, or comma-separated):
        </label>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={8}
          placeholder={'https://example.com\nhttps://secure-login-example.tk/login'}
          className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 font-mono text-sm"
          disabled={loading}
        />
        <div className="flex items-center justify-between mt-3">
          <span className="text-xs text-slate-500">{urls.length} URL{urls.length === 1 ? '' : 's'} detected</span>
          <button
            type="submit"
            disabled={loading || urls.length === 0}
            className="px-6 py-2.5 bg-cyan-600 text-white font-medium rounded-lg hover:bg-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Scanning…' : `Scan ${urls.length > 100 ? 100 : urls.length} URL${urls.length === 1 ? '' : 's'}`}
          </button>
        </div>
      </form>

      {loading && (
        <div className="text-center py-8">
          <div className="animate-spin h-8 w-8 border-2 border-cyan-500 border-t-transparent rounded-full mx-auto mb-3" />
          <p className="text-slate-400">Scanning URLs in batches…</p>
        </div>
      )}

      {error && (
        <div className="bg-red-950/50 border border-red-800 text-red-300 rounded-xl p-4 mb-6 animate-fade-up">{error}</div>
      )}

      {results.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-slate-800 animate-fade-up">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-900 text-left text-slate-300">
                <th className="px-4 py-3 font-medium">URL</th>
                <th className="px-4 py-3 font-medium">Score</th>
                <th className="px-4 py-3 font-medium">Verdict</th>
                <th className="px-4 py-3 font-medium">Top Signal</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 bg-slate-900/50">
              {results.map((r) => {
                const style = verdictStyle(r.verdict)
                const failing = r.signals.find((s) => s.available && !s.passed)
                return (
                  <tr key={r.scan_id} className="hover:bg-slate-800/50">
                    <td className="px-4 py-3 text-slate-300 break-all max-w-xs truncate">{r.url}</td>
                    <td className={`px-4 py-3 font-mono font-semibold ${style.text}`}>{r.score ?? '—'}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-block px-2 py-0.5 rounded-full border text-xs ${style.chip}`}>
                        {r.verdict}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-400 text-xs">
                      {failing ? SIGNAL_LABELS[failing.signal_name] || failing.signal_name : 'No red flags'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {errors.length > 0 && (
        <div className="mt-4 space-y-2">
          {errors.map((e) => (
            <div key={e.url} className={`rounded-lg border px-3 py-2 text-xs ${signalTone(false, false)} text-slate-400`}>
              {e.url} — {e.error}
            </div>
          ))}
        </div>
      )}
    </main>
  )
}