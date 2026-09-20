import type { Stat } from '../../types'
import { StatGrid } from '../artifacts/StatGrid'
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
        <div className="mt-5 border-t border-line-soft pt-5">
          <StatGrid items={stats} />
        </div>
      )}
    </section>
  )
}
