interface SignalResult {
  signal_name: string
  category: string
  passed: boolean
  deduction: number
  detail: string
  available: boolean
  availability_reason?: string | null
}

interface SignalListProps {
  signals: SignalResult[]
}

const CATEGORY_LABELS: Record<string, string> = {
  ssl: 'SSL/TLS',
  domain_trust: 'Domain Trust',
  hosting: 'Hosting',
  reputation: 'Reputation',
  content: 'Content',
  brand: 'Brand Impersonation',
}

export default function SignalList({ signals }: SignalListProps) {
  return (
    <div className="space-y-2">
      <h2 className="text-lg font-semibold text-gray-700 mb-3">Signal Breakdown</h2>
      {signals.map((s) => (
        <div
          key={s.signal_name}
          className={`rounded-lg border p-4 ${
            !s.available
              ? 'bg-gray-50 border-gray-200'
              : s.passed
                ? 'bg-green-50 border-green-200'
                : 'bg-red-50 border-red-200'
          }`}
        >
          <div className="flex items-start gap-3">
            <span className="text-xl mt-0.5">
              {!s.available ? '!' : s.passed ? '✓' : '×'}
            </span>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <span className="font-medium text-sm">
                  {CATEGORY_LABELS[s.category] || s.category}
                </span>
                {s.available && (
                  <span className={`text-xs font-mono px-2 py-0.5 rounded ${
                    s.deduction === 0
                      ? 'bg-green-100 text-green-700'
                      : 'bg-red-100 text-red-700'
                  }`}>
                    {s.deduction === 0 ? '0 pts' : `-${s.deduction} pts`}
                  </span>
                )}
              </div>
              {!s.available && (
                <p className="text-xs font-medium text-gray-500 mt-1">
                  {s.availability_reason === 'not_configured' ? 'Not configured on this server' : 'Check failed or timed out'}
                </p>
              )}
              <p className="text-sm text-gray-600 mt-1">{s.detail}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
