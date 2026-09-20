import { formatValue, type ChartModel } from './chartData'

interface ChartTooltipProps {
  active?: boolean
  /** A merged row for lines and bars; a single `{ x, y, series }` dot for scatter plots. */
  point?: Record<string, number | string>
  model: ChartModel
  xLabel: string
  yLabel: string
}

function Entry({ label, value, muted }: { label: string; value: string; muted?: boolean }) {
  return (
    <div className={`flex justify-between gap-6 ${muted ? 'text-muted' : ''}`}>
      <span className="max-w-[160px] truncate">{label}</span>
      <span className="font-mono">{value}</span>
    </div>
  )
}

export function ChartTooltip({ active, point, model, xLabel, yLabel }: ChartTooltipProps) {
  if (!active || !point) return null
  const x = model.formatX(Number(point.x))

  if (model.kind === 'scatter') {
    return (
      <div className="rounded-lg border border-line bg-white px-3 py-2 text-xs">
        {model.series.length > 1 && <div className="max-w-[200px] truncate pb-1 text-muted">{point.series}</div>}
        <Entry label={xLabel || 'x'} value={model.xMode === 'number' ? formatValue(Number(point.x)) : x} />
        <Entry label={yLabel || 'y'} value={formatValue(Number(point.y))} />
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-line bg-white px-3 py-2 text-xs">
      <div className="max-w-[200px] truncate pb-1 text-muted">{x}</div>
      {model.series
        .filter((series) => typeof point[series.key] === 'number')
        .map((series, index) => (
          <Entry key={series.key} label={series.name} value={formatValue(Number(point[series.key]))} muted={index > 0} />
        ))}
    </div>
  )
}
