import { Bar, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis } from 'recharts'
import { formatNumber, PLOT_HEIGHT, type ChartModel } from './chartData'
import { ChartTooltip } from './ChartTooltip'

const MUTED = '#8c8c8c'
const LINE_SOFT = '#efefef'
const FILL = '#f4f4f4'
const DENSE = 150
const DASHES = [undefined, undefined, '4 3', '2 3']

const tick = { fontSize: 11, fill: MUTED, fontFamily: 'var(--font-mono)' }

interface DotProps {
  cx?: number
  cy?: number
  fill?: string
  fillOpacity?: number
}

function Dot({ cx, cy, fill, fillOpacity }: DotProps) {
  return Number.isFinite(cx) && Number.isFinite(cy) ? <circle cx={cx} cy={cy} r={3} fill={fill} fillOpacity={fillOpacity} /> : null
}

export function ChartPlot({ model, xLabel, yLabel }: { model: ChartModel; xLabel: string; yLabel: string }) {
  const { kind, series } = model
  const total = series.reduce((sum, entry) => sum + entry.count, 0)
  // Lines and dots overlap, so fainter series are drawn first and the ink one sits on top; bars sit side by side.
  const drawOrder = kind === 'bar' ? series : [...series].reverse()
  const dipsBelowZero = kind === 'bar' && series.some((entry) => entry.points.some((point) => point.y < 0))

  return (
    <div data-testid="chart-plot">
      <ResponsiveContainer width="100%" height={PLOT_HEIGHT}>
        <ComposedChart data={model.rows} margin={{ top: 8, right: 20, bottom: 0, left: 0 }} barCategoryGap="30%" barGap={2}>
          <XAxis
            dataKey="x"
            type={kind === 'bar' ? 'category' : 'number'}
            domain={kind === 'bar' ? undefined : model.xDomain}
            ticks={kind === 'bar' ? undefined : model.xTicks}
            tickFormatter={model.formatTick}
            minTickGap={16}
            tickLine={false}
            axisLine={{ stroke: LINE_SOFT }}
            tick={tick}
            tickMargin={8}
          />
          <YAxis
            dataKey={kind === 'scatter' ? 'y' : undefined}
            width="auto"
            domain={kind === 'bar' ? undefined : ['auto', 'auto']}
            tickCount={4}
            tickFormatter={formatNumber}
            tickLine={false}
            axisLine={false}
            tick={tick}
            tickMargin={8}
          />
          <Tooltip
            cursor={kind === 'line' ? { stroke: LINE_SOFT } : kind === 'bar' ? { fill: FILL } : false}
            content={({ active, payload }) => <ChartTooltip active={active} point={payload?.[0]?.payload} model={model} xLabel={xLabel} yLabel={yLabel} />}
            isAnimationActive={false}
          />
          {dipsBelowZero && <ReferenceLine y={0} stroke={LINE_SOFT} />}
          {drawOrder.map((entry) => {
            const index = series.indexOf(entry)
            if (kind === 'bar') {
              return <Bar key={entry.key} dataKey={entry.key} fill={entry.color} radius={[2, 2, 0, 0]} maxBarSize={44} isAnimationActive={false} />
            }
            if (kind === 'scatter') {
              return (
                <Scatter
                  key={entry.key}
                  data={entry.points.map((point) => ({ ...point, series: entry.name }))}
                  fill={entry.color}
                  fillOpacity={total > DENSE ? 0.55 : 1}
                  shape={Dot}
                  isAnimationActive={false}
                />
              )
            }
            return (
              <Line
                key={entry.key}
                dataKey={entry.key}
                stroke={entry.color}
                strokeWidth={1.5}
                strokeDasharray={DASHES[Math.min(index, DASHES.length - 1)]}
                dot={entry.count === 1 ? { r: 3, fill: entry.color, strokeWidth: 0 } : false}
                activeDot={{ r: 3, strokeWidth: 0 }}
                connectNulls
                isAnimationActive={false}
              />
            )
          })}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
