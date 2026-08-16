import { useState } from 'react'
import { CATEGORY_LABELS, SIGNAL_LABELS, signalTone } from '@/lib/verdicts'

interface SignalResult {
  signal_name: string
  category: string
  passed: boolean
  deduction: number
  detail: string
  available: boolean
  availability_reason?: string | null
  raw_data?: Record<string, unknown> | null
}

interface SignalListProps {
  signals: SignalResult[]
}

export default function SignalList({ signals }: SignalListProps) {
  const [open, setOpen] = useState<string | null>(null)

  return (
    <div className="space-y-2 animate-fade-up">
      <h2 className="text-lg font-semibold text-slate-200 mb-3">Signal Breakdown</h2>
      {signals.map((s) => {
        const tone = signalTone(s.available, s.passed)
        const label = SIGNAL_LABELS[s.signal_name] || CATEGORY_LABELS[s.category] || s.signal_name
        const isOpen = open === s.signal_name

        return (
          <div key={s.signal_name} className={`rounded-xl border p-4 ${tone}`}>
            <button
              type="button"
              onClick={() => setOpen(isOpen ? null : s.signal_name)}
              className="w-full flex items-start gap-3 text-left"
            >
              <span className="text-lg mt-0.5">
                {!s.available ? '…' : s.passed ? '✓' : '✕'}
              </span>
              <div className="flex-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-sm text-slate-100">{label}</span>
                  {s.available && (
                    <span
                      className={`text-xs font-mono px-2 py-0.5 rounded ${
                        s.deduction === 0
                          ? 'bg-emerald-500/15 text-emerald-300'
                          : 'bg-red-500/15 text-red-300'
                      }`}
                    >
                      {s.deduction === 0 ? '0 pts' : `-${s.deduction} pts`}
                    </span>
                  )}
                </div>
                <p className="text-sm text-slate-400 mt-1">{s.detail}</p>
                {!s.available && (
                  <p className="text-xs font-medium text-slate-500 mt-1">
                    {s.availability_reason === 'not_configured' || s.availability_reason === 'model_unavailable'
                      ? 'Not available in this deployment'
                      : 'Check failed or timed out'}
                  </p>
                )}
                <span className="text-xs text-slate-500 mt-1 inline-block">
                    {isOpen ? 'Hide details ▲' : 'Details ▼'}
                  </span>
              </div>
            </button>
            {isOpen && (
              <div className="mt-3 pl-7">
                <pre className="text-xs text-slate-400 bg-slate-950/60 border border-slate-800 rounded-lg p-3 overflow-x-auto">
                  {JSON.stringify(
                    s.raw_data ? { passed: s.passed, deduction: s.deduction, ...s.raw_data } : { passed: s.passed, deduction: s.deduction },
                    null,
                    2,
                  )}
                </pre>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}