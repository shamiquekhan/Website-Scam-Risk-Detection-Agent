interface ScoreCardProps {
  score: number | null
  verdict: string
  summary: string
  completedSignals: number
  totalSignals: number
  confidence: number
}

export default function ScoreCard({ score, verdict, summary, completedSignals, totalSignals, confidence }: ScoreCardProps) {
  const colorMap: Record<string, string> = {
    Safe: 'bg-green-100 border-green-500 text-green-800',
    Caution: 'bg-yellow-100 border-yellow-500 text-yellow-800',
    'High Risk': 'bg-red-100 border-red-500 text-red-800',
    'Insufficient Data': 'bg-orange-100 border-orange-500 text-orange-800',
  }

  const badgeColor = colorMap[verdict] || 'bg-gray-100 border-gray-500 text-gray-800'

  return (
    <div className={`rounded-lg border-2 p-6 mb-6 ${badgeColor}`}>
      <div className="flex items-center justify-between mb-4">
        <div>
          {score === null ? (
            <div className="text-3xl font-bold">No score</div>
          ) : (
            <>
              <div className="text-5xl font-bold">{score}</div>
              <div className="text-sm opacity-75">out of 100</div>
            </>
          )}
        </div>
        <div className="text-right">
          <div className="text-2xl font-semibold">{verdict}</div>
          <div className="text-sm opacity-75">Risk Level</div>
        </div>
      </div>
      <div className="text-sm opacity-75 mb-2">
        Evidence: {completedSignals} of {totalSignals} checks completed ({confidence}% confidence)
      </div>
      {summary && (
        <p className="text-sm leading-relaxed border-t border-current/20 pt-3 mt-2">
          {summary}
        </p>
      )}
    </div>
  )
}
