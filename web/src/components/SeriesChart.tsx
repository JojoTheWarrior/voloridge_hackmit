import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis } from 'recharts'
import type { MissionResult, SeriesPoint } from '../types'

const INK = '#0a0a0a'
const FAINT = '#bdbdbd'
const MUTED = '#8c8c8c'
const LINE_SOFT = '#efefef'

const shortDate = (iso: string) =>
  new Date(`${iso}T00:00:00Z`).toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' })

interface ChartTooltipProps {
  active?: boolean
  point?: SeriesPoint
  result: MissionResult
}

function ChartTooltip({ active, point, result }: ChartTooltipProps) {
  if (!active || !point) return null
  const { a, b } = point
  return (
    <div className="rounded-lg border border-line bg-white px-3 py-2 text-xs">
      <div className="pb-1 text-muted">{shortDate(point.date)}</div>
      <div className="flex justify-between gap-6">
        <span>{result.seriesA}</span>
        <span className="font-mono">{a.toFixed(2)}</span>
      </div>
      <div className="flex justify-between gap-6 text-muted">
        <span>{result.seriesB}</span>
        <span className="font-mono">{b.toFixed(2)}</span>
      </div>
    </div>
  )
}

export function SeriesChart({ result }: { result: MissionResult }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={result.points} margin={{ top: 8, right: 24, bottom: 0, left: 24 }}>
        <XAxis
          dataKey="date"
          tickFormatter={shortDate}
          minTickGap={72}
          tickLine={false}
          axisLine={{ stroke: LINE_SOFT }}
          tick={{ fontSize: 11, fill: MUTED, fontFamily: 'var(--font-mono)' }}
          tickMargin={8}
        />
        <Tooltip
          cursor={{ stroke: LINE_SOFT }}
          content={({ active, payload }) => <ChartTooltip active={active} point={payload?.[0]?.payload} result={result} />}
          isAnimationActive={false}
        />
        <Line dataKey="b" stroke={FAINT} strokeWidth={1.5} dot={false} activeDot={{ r: 3, strokeWidth: 0 }} animationDuration={500} />
        <Line dataKey="a" stroke={INK} strokeWidth={1.5} dot={false} activeDot={{ r: 3, strokeWidth: 0 }} animationDuration={500} />
      </LineChart>
    </ResponsiveContainer>
  )
}
