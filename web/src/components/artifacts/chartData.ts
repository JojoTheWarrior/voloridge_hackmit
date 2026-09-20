import type { ChartArtifact } from '../../types'
import { dateTicks, niceTicks } from './chartTicks'
import { truncate } from './text'

export type ChartKind = ChartArtifact['kind']
export type XMode = 'number' | 'date' | 'category'

export interface ChartRow {
  x: number
  [seriesKey: string]: number
}

export interface ModelSeries {
  key: string
  name: string
  color: string
  count: number
  points: { x: number; y: number }[]
}

export interface ChartModel {
  kind: ChartKind
  xMode: XMode
  series: ModelSeries[]
  /** One row per distinct x, for line and bar charts. */
  rows: ChartRow[]
  xDomain: [number, number]
  xTicks: number[]
  formatX: (x: number) => string
  /** `formatX`, cut short enough to sit under an axis. */
  formatTick: (x: number) => string
  empty: boolean
}

/** Shared by the plot and the placeholder shown while the chart library loads. */
export const PLOT_HEIGHT = 220

const COLORS = ['#0a0a0a', '#bdbdbd', '#d0d0d0', '#dcdcdc']
const KINDS: ChartKind[] = ['line', 'scatter', 'bar']
const ISO_DATE = /^\d{4}-\d{2}-\d{2}(T[\d:.]+(Z|[+-]\d{2}:?\d{2})?)?$/
const DAY_MS = 86_400_000
const YEAR_MS = 366 * DAY_MS
const SCATTER_PAD = 0.04
const MAX_TICK_LABEL = 12

export const seriesColor = (index: number) => COLORS[Math.min(index, COLORS.length - 1)]

const compact = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 })

export function formatNumber(value: number): string {
  if (!Number.isFinite(value)) return '—'
  const size = Math.abs(value)
  // Three significant digits would turn the year 2019 into 2020, so whole-number ranges are only rounded.
  const text = size >= 10_000 ? compact.format(value) : String(size >= 100 ? Math.round(value) : Number(value.toPrecision(3)))
  return text.replace('-', '−')
}

const plain = new Intl.NumberFormat('en-US', { maximumFractionDigits: 3 })

/** Fuller precision than the axis ticks, for tooltips. */
export const formatValue = (value: number) => (Number.isFinite(value) ? plain.format(value).replace('-', '−') : '—')

type RawX = number | string

const isDate = (x: RawX) => typeof x === 'string' && ISO_DATE.test(x) && Number.isFinite(Date.parse(x))
const isNumeric = (x: RawX) => (typeof x === 'number' ? Number.isFinite(x) : x.trim() !== '' && Number.isFinite(Number(x)))

function validPoints(points: unknown): [RawX, number][] {
  if (!Array.isArray(points)) return []
  return points.filter(
    (point): point is [RawX, number] =>
      Array.isArray(point) &&
      (typeof point[0] === 'string' || (typeof point[0] === 'number' && Number.isFinite(point[0]))) &&
      typeof point[1] === 'number' &&
      Number.isFinite(point[1]),
  )
}

function dateFormatter(span: number) {
  const options: Intl.DateTimeFormatOptions =
    span > YEAR_MS ? { month: 'short', year: 'numeric', timeZone: 'UTC' } : { month: 'short', day: 'numeric', timeZone: 'UTC' }
  return (x: number) => new Date(x).toLocaleDateString('en-US', options)
}

const span = (values: number[]) => (values.length ? Math.max(...values) - Math.min(...values) : 0)

function domainOf(values: number[], pad: number, unit: number): [number, number] {
  const min = Math.min(...values)
  const max = Math.max(...values)
  if (min === max) return [min - unit, max + unit]
  const margin = (max - min) * pad
  return [min - margin, max + margin]
}

export function buildChartModel(artifact: ChartArtifact): ChartModel {
  const kind = KINDS.includes(artifact.kind) ? artifact.kind : 'line'
  const raw = (Array.isArray(artifact.series) ? artifact.series : [])
    .map((series, index) => ({ name: series?.name ? String(series.name) : `Series ${index + 1}`, points: validPoints(series?.points) }))
    .filter((series) => series.points.length > 0)

  const xs = raw.flatMap((series) => series.points.map(([x]) => x))
  const allDates = xs.length > 0 && xs.every(isDate)
  const xMode: XMode = kind === 'bar' ? 'category' : allDates ? 'date' : xs.every(isNumeric) ? 'number' : 'category'

  const categories: RawX[] = []
  const position = (x: RawX) => {
    if (xMode === 'date') return Date.parse(x as string)
    if (xMode === 'number') return Number(x)
    const known = categories.findIndex((category) => String(category) === String(x))
    return known >= 0 ? known : categories.push(x) - 1
  }

  const rowsByX = new Map<number, ChartRow>()
  const series = raw.map((entry, index): ModelSeries => {
    const key = `s${index}`
    const points = entry.points.map(([rawX, y]) => {
      const x = position(rawX)
      rowsByX.set(x, { ...(rowsByX.get(x) ?? { x }), [key]: y })
      return { x, y }
    })
    return { key, name: entry.name, color: seriesColor(index), count: points.length, points }
  })
  const rows = [...rowsByX.values()].sort((a, b) => a.x - b.x)
  const positions = rows.map((row) => row.x)

  const formatDate = dateFormatter(allDates ? span(xs.map((x) => Date.parse(x as string))) : 0)
  const formatCategory = (x: number) => {
    const value = categories[x]
    if (value === undefined) return ''
    if (allDates) return formatDate(Date.parse(value as string))
    return typeof value === 'number' ? formatNumber(value) : value
  }

  const xDomain: [number, number] =
    positions.length === 0
      ? [0, 1]
      : xMode === 'category'
        ? [-0.5, categories.length - 0.5]
        : domainOf(positions, kind === 'scatter' ? SCATTER_PAD : 0, xMode === 'date' ? DAY_MS : 1)

  const formatX = xMode === 'date' ? formatDate : xMode === 'number' ? formatNumber : formatCategory

  return {
    kind,
    xMode,
    series,
    rows,
    xDomain,
    xTicks: xMode === 'category' ? positions : xMode === 'date' ? dateTicks(...xDomain) : niceTicks(...xDomain),
    formatX,
    formatTick: (x) => truncate(formatX(x), MAX_TICK_LABEL),
    empty: series.length === 0,
  }
}
