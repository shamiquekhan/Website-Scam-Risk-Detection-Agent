interface LoadingSkeletonProps {
  checks: string[]
}

export default function LoadingSkeleton({ checks }: LoadingSkeletonProps) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 mb-6 animate-fade-up">
      <div className="flex items-center gap-3 mb-5">
        <div className="animate-spin h-6 w-6 border-2 border-cyan-500 border-t-transparent rounded-full" />
        <p className="text-slate-300 text-sm">Running 11 independent checks...</p>
      </div>
      <div className="space-y-3">
        {checks.map((check, index) => (
          <div key={check} className="flex items-center gap-3">
            <span className="text-xs text-cyan-400 font-mono w-6 text-right">{index + 1}</span>
            <div className="flex-1 h-3 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-cyan-600/70 rounded-full animate-pulse"
                style={{ width: `${100 - index * 12}%` }}
              />
            </div>
            <span className="text-xs text-slate-400 w-40 text-right truncate">{check}</span>
          </div>
        ))}
      </div>
    </div>
  )
}