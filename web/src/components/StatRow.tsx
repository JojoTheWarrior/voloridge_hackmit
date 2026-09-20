import { formatCorrelation, formatLag, formatP } from '../format'
import type { MissionResult } from '../types'

export function StatRow({ result }: { result: MissionResult }) {
  const stats = [
    ['Correlation', formatCorrelation(result.correlation)],
    ['Best lag', formatLag(result.bestLagDays)],
    ['p-value', formatP(result.pValue)],
    ['Sample', `${result.n} days`],
  ]
  return (
    <dl className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
      {stats.map(([label, value]) => (
        <div key={label}>
          <dt className="text-xs text-muted">{label}</dt>
          <dd className="mt-0.5 font-mono text-lg tracking-tight">{value}</dd>
        </div>
      ))}
    </dl>
  )
}
