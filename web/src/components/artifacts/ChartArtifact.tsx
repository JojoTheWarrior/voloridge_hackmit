import { lazy, Suspense, useMemo } from 'react'
import type { ChartArtifact as ChartSpec } from '../../types'
import { buildChartModel, PLOT_HEIGHT, type ChartKind, type ModelSeries } from './chartData'
import { EmptyBody } from './EmptyBody'
import { asText } from './text'

// The chart library is most of the bundle; only threads that contain a chart need it.
const ChartPlot = lazy(() => import('./ChartPlot').then((m) => ({ default: m.ChartPlot })))

const SWATCH: Record<ChartKind, string> = {
  line: 'h-0 w-4 border-t-[1.5px]',
  bar: 'h-2 w-2 rounded-[2px] border-4',
  scatter: 'h-1.5 w-1.5 rounded-full border-[3px]',
}

function LegendItem({ series, kind, primary }: { series: ModelSeries; kind: ChartKind; primary: boolean }) {
  return (
    <span className={`flex min-w-0 items-center gap-2 ${primary ? '' : 'text-muted'}`}>
      <span aria-hidden="true" className={`shrink-0 ${SWATCH[kind]}`} style={{ borderColor: series.color }} />
      <span className="truncate" title={series.name}>
        {series.name}
      </span>
    </span>
  )
}

export function ChartArtifact({ artifact }: { artifact: ChartSpec }) {
  const model = useMemo(() => buildChartModel(artifact), [artifact])
  if (model.empty) return <EmptyBody />

  const xLabel = asText(artifact.xLabel)
  const yLabel = asText(artifact.yLabel)
  const legend = model.series.length > 1

  return (
    <div>
      {(yLabel || legend) && (
        <div className="flex flex-wrap items-center justify-between gap-x-5 gap-y-1 pb-3">
          <span className="max-w-full truncate text-[11px] text-muted" title={yLabel}>
            {yLabel}
          </span>
          {legend && (
            <div className="flex min-w-0 flex-wrap gap-x-5 gap-y-1 text-xs">
              {model.series.map((series, index) => (
                <LegendItem key={series.key} series={series} kind={model.kind} primary={index === 0} />
              ))}
            </div>
          )}
        </div>
      )}
      <Suspense fallback={<div style={{ height: PLOT_HEIGHT }} />}>
        <ChartPlot model={model} xLabel={xLabel} yLabel={yLabel} />
      </Suspense>
      {xLabel && (
        <p className="truncate pt-2 pr-5 text-right text-[11px] text-muted" title={xLabel}>
          {xLabel}
        </p>
      )}
    </div>
  )
}
