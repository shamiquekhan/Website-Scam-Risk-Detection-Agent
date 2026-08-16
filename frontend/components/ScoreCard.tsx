import { verdictStyle } from '@/lib/verdicts'

interface ScoreCardProps {
  score: number | null
  verdict: string
  summary: string
  completedSignals: number
  totalSignals: number
  confidence: number
}

const RADIUS = 90
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

export default function ScoreCard({ score, verdict, summary, completedSignals, totalSignals, confidence }: ScoreCardProps) {
  const style = verdictStyle(verdict)
  const numericScore = score ?? 0
  const offset = CIRCUMFERENCE - (numericScore / 100) * CIRCUMFERENCE

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 mb-6 animate-fade-up">
      <div className="flex flex-col sm:flex-row items-center gap-6">
        <div className="relative shrink-0">
          <svg width="220" height="220" viewBox="0 0 220 220" className="rotate-[-90deg]">
            <circle cx="110" cy="110" r={RADIUS} fill="none" stroke="#1e293b" strokeWidth="16" />
            {score !== null && (
              <circle
                cx="110"
                cy="110"
                r={RADIUS}
                fill="none"
                stroke={style.ring}
                strokeWidth="16"
                strokeLinecap="round"
                strokeDasharray={CIRCUMFERENCE}
                strokeDashoffset={offset}
                className="animate-gauge transition-all duration-1000 ease-out"
                style={{ ['--gauge-full' as string]: `${CIRCUMFERENCE}` }}
              />
            )}
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            {score === null ? (
              <div className="text-center">
                <div className="text-xl font-bold text-slate-300">No Score</div>
                <div className="text-xs text-slate-500 mt-1">Insufficient Data</div>
              </div>
            ) : (
              <div className="text-center">
                <div className={`text-5xl font-bold ${style.text}`}>{score}</div>
                <div className="text-xs text-slate-500 mt-1">out of 100</div>
              </div>
            )}
          </div>
        </div>

        <div className="flex-1 text-center sm:text-left">
          <span className={`inline-block px-3 py-1 rounded-full border text-sm font-medium ${style.chip}`}>
            {verdict}
          </span>
          <div className="text-sm text-slate-400 mt-4">
            <span className="text-slate-200 font-medium">{completedSignals}</span> of{' '}
            <span className="text-slate-200 font-medium">{totalSignals}</span> checks completed -{' '}
            <span className="text-slate-200 font-medium">{confidence}%</span> confidence
          </div>
          {summary && (
            <p className="text-sm leading-relaxed text-slate-300 mt-3 border-t border-slate-800 pt-3">
              {summary}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}