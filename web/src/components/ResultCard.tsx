import { lazy, Suspense } from 'react'
import type { MissionResult } from '../types'
import { StatRow } from './StatRow'

// The chart library is most of the bundle; only mission pages with a result need it.
const SeriesChart = lazy(() => import('./SeriesChart').then((m) => ({ default: m.SeriesChart })))

function LegendItem({ label, className }: { label: string; className: string }) {
  return (
    <span className="flex items-center gap-2">
      <span aria-hidden="true" className={`h-px w-4 border-t-[1.5px] ${className}`} />
      {label}
    </span>
  )
}

export function ResultCard({ result }: { result: MissionResult }) {
  return (
    <section aria-label="Result" className="fade-in rounded-xl border border-line p-5">
      <div className="flex flex-wrap items-center justify-between gap-x-5 gap-y-1 pb-3 text-xs">
        <div className="flex flex-wrap gap-x-5 gap-y-1">
          <LegendItem label={result.seriesA} className="border-ink" />
          <LegendItem label={result.seriesB} className="border-faint text-muted" />
        </div>
        <span className="text-muted">Daily, standardized</span>
      </div>
      <Suspense fallback={<div className="h-[220px]" />}>
        <SeriesChart result={result} />
      </Suspense>

      <div className="mt-5 border-t border-line-soft pt-5">
        <StatRow result={result} />
      </div>

      <div className="mt-5 flex flex-col gap-3 border-t border-line-soft pt-5 text-[15px] leading-[1.65]">
        {result.note.split(/\n{2,}/).map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
        <p className="font-medium">{result.verdict}</p>
      </div>
    </section>
  )
}
