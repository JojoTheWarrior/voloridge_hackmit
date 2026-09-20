import type { Stat } from '../../types'
import { Prose } from './Prose'

interface ConclusionCardProps {
  verdict: string
  summary: string
  stats: Stat[]
}

export function ConclusionCard({ verdict, summary, stats }: ConclusionCardProps) {
  return (
    <section aria-label="Conclusion" className="fade-in rounded-xl border border-line p-5">
      <p className="text-[15px] leading-[1.65] font-medium">{verdict}</p>
      <Prose text={summary} className="mt-3 empty:hidden" />
      {stats.length > 0 && (
        <dl className="mt-5 grid grid-cols-2 gap-x-6 gap-y-4 border-t border-line-soft pt-5 sm:grid-cols-4">
          {stats.map((stat) => (
            <div key={stat.label}>
              <dt className="text-xs text-muted">{stat.label}</dt>
              <dd className="mt-0.5 font-mono text-lg tracking-tight">{stat.value}</dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  )
}
