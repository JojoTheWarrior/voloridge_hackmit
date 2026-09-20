import { formatCorrelation, formatLag, formatP } from '../format'
import type { ChartArtifact, ChartSeries, Stat, TableArtifact } from '../types'

const N_DAYS = 120
const MAX_LAG = 7
const END_DATE = Date.UTC(2026, 8, 15)
const DAY_MS = 86_400_000
// Daily series are autocorrelated, so far fewer than N_DAYS observations are independent.
const EFFECTIVE_N = N_DAYS / 4
const WEAK = 0.2
const LARGEST_MOVES = 5

function hash(text: string): number {
  let h = 2166136261
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return h >>> 0
}

function mulberry32(seed: number): () => number {
  let a = seed
  return () => {
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function gaussian(rand: () => number): number {
  return Math.sqrt(-2 * Math.log(1 - rand())) * Math.cos(2 * Math.PI * rand())
}

function ar1(rand: () => number, length: number): number[] {
  const out = [gaussian(rand)]
  for (let i = 1; i < length; i++) out.push(0.85 * out[i - 1] + gaussian(rand))
  return out
}

function zscore(values: number[]): number[] {
  const mean = values.reduce((s, v) => s + v, 0) / values.length
  const sd = Math.sqrt(values.reduce((s, v) => s + (v - mean) ** 2, 0) / values.length) || 1
  return values.map((v) => (v - mean) / sd)
}

function pearson(x: number[], y: number[]): number {
  const zx = zscore(x)
  const zy = zscore(y)
  return zx.reduce((s, v, i) => s + v * zy[i], 0) / x.length
}

/** Two-sided p-value for a correlation, via the Fisher z normal approximation. */
function pValueFor(r: number, n: number): number {
  const z = Math.abs(Math.atanh(Math.min(Math.abs(r), 0.999999))) * Math.sqrt(n - 3)
  const x = z / Math.SQRT2
  const t = 1 / (1 + 0.3275911 * x)
  const poly = t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429))))
  return Math.min(1, poly * Math.exp(-x * x))
}

function isReliable(r: number, p: number): boolean {
  return p < 0.05 && Math.abs(r) >= WEAK
}

function seriesNames(hypothesis: string): [string, string] {
  const match = hypothesis.match(
    /^(?:do|does|did|is|are|can)\s+(.+?)\s+(?:vs\.?|versus|leads?|predicts?|moves?|drives?|affects?|tracks?)\s+(.+?)\??$/i,
  )
  if (!match) return ['Signal', 'Target']
  const capitalize = (s: string) => s[0].toUpperCase() + s.slice(1)
  return [capitalize(match[1]), capitalize(match[2])]
}

function writeUp(a: string, b: string, r: number, lag: number, p: number): { summary: string; verdict: string } {
  const caveat = `This is a correlation over ${N_DAYS} days, not a causal claim. A shared driver could explain both series.`
  if (!isReliable(r, p)) {
    return {
      summary: `${a} and ${b} show no dependable relationship at any lag up to ${MAX_LAG} days. The strongest correlation found was ${r.toFixed(2)}, which a permutation test cannot tell apart from chance.\n\nA null result is still a result: this pairing can be dropped from the queue.`,
      verdict: 'No reliable link.',
    }
  }
  const direction = r > 0 ? 'move together' : 'move in opposite directions'
  const finding =
    lag === 0
      ? `${a} and ${b} ${direction} on the same day.`
      : `${a} leads ${b} by ${lag} ${lag === 1 ? 'day' : 'days'}, and the two ${direction}.`
  return {
    summary: `${finding} The link holds up under a permutation test, so it is unlikely to be chance.\n\n${caveat}`,
    verdict: Math.abs(r) >= 0.5 ? 'A strong link.' : 'A real but modest link.',
  }
}

export interface FindingsShape {
  seriesA?: string
  seriesB?: string
  /** Target correlation at the true lag, -1 to 1. */
  strength?: number
  lagDays?: number
}

export interface Findings {
  chart: ChartArtifact
  /** The correlation at every lag tried. */
  lags: ChartArtifact
  /** The headline correlation again on parts of the window. */
  checks: TableArtifact
  conclusion: { verdict: string; summary: string; stats: Stat[] }
}

/** Deterministic mock findings: the same hypothesis always yields the same chart and stats. */
export function buildFindings(hypothesis: string, shape: FindingsShape = {}): Findings {
  const rand = mulberry32(hash(hypothesis))
  const strength = shape.strength ?? rand() * 0.7
  const trueLag = shape.lagDays ?? Math.floor(rand() * 5)
  const [parsedA, parsedB] = seriesNames(hypothesis)
  const seriesA = shape.seriesA ?? parsedA
  const seriesB = shape.seriesB ?? parsedB

  const length = N_DAYS + MAX_LAG
  const a = zscore(ar1(rand, length))
  const lagged = zscore(a.map((_, i) => a[Math.max(0, i - trueLag)]))
  // Strip the noise of any chance correlation with the driver so the planted strength is what gets measured.
  const rawNoise = zscore(ar1(rand, length))
  const overlap = pearson(rawNoise, lagged)
  const noise = zscore(rawNoise.map((v, i) => v - overlap * lagged[i]))
  const b = zscore(lagged.map((v, i) => strength * v + Math.sqrt(1 - strength ** 2) * noise[i]))

  const target = b.slice(MAX_LAG)
  const leadBy = (lag: number) => a.slice(MAX_LAG - lag, length - lag)
  const sweep = Array.from({ length: MAX_LAG + 1 }, (_, lag) => pearson(leadBy(lag), target))
  const bestLagDays = sweep.reduce((best, r, lag) => (Math.abs(r) > Math.abs(sweep[best]) ? lag : best), 0)
  const correlation = sweep[bestLagDays]

  const dates = a.slice(MAX_LAG).map((_, i) => new Date(END_DATE - (N_DAYS - 1 - i) * DAY_MS).toISOString().slice(0, 10))
  const pointsOf = (values: number[]): ChartSeries['points'] => dates.map((date, i) => [date, Number(values[i + MAX_LAG].toFixed(3))])

  const pValue = pValueFor(correlation, EFFECTIVE_N)
  const shownCorrelation = formatCorrelation(correlation)

  const lead = leadBy(bestLagDays)
  const half = N_DAYS / 2
  const largest = new Set(
    target
      .map((v, i) => [Math.abs(v), i])
      .sort(([x], [y]) => y - x)
      .slice(0, LARGEST_MOVES)
      .map(([, i]) => i),
  )
  const calm = (values: number[]) => values.filter((_, i) => !largest.has(i))
  const holds = (r: number) => (Math.sign(r) === Math.sign(correlation) && Math.abs(r) >= WEAK ? 'Yes' : 'No')
  const check = (label: string, r: number) => [label, formatCorrelation(r), holds(r)]
  return {
    chart: {
      id: 'a1',
      type: 'chart',
      kind: 'line',
      title: `${seriesA} vs ${seriesB}`,
      caption: 'Daily, standardized',
      headline: `r = ${shownCorrelation}`,
      series: [
        { name: seriesA, points: pointsOf(a) },
        { name: seriesB, points: pointsOf(b) },
      ],
    },
    lags: {
      id: 'a2',
      type: 'chart',
      kind: 'bar',
      title: `Correlation when ${seriesA} leads`,
      caption: 'Each bar shifts the first series that many days ahead of the second',
      headline: `Best at ${formatLag(bestLagDays).toLowerCase()}`,
      xLabel: 'Lag in days',
      yLabel: 'Correlation',
      series: [{ name: 'Correlation', points: sweep.map((r, lag) => [String(lag), Number(r.toFixed(3))]) }],
    },
    checks: {
      id: 'a3',
      type: 'table',
      title: 'Does it hold on parts of the window',
      columns: ['Check', 'Correlation', 'Holds'],
      rows: [
        ['Full window', shownCorrelation, isReliable(correlation, pValue) ? 'Yes' : 'No'],
        check('First half', pearson(lead.slice(0, half), target.slice(0, half))),
        check('Second half', pearson(lead.slice(half), target.slice(half))),
        check(`Without the ${LARGEST_MOVES} largest moves`, pearson(calm(lead), calm(target))),
      ],
    },
    conclusion: {
      ...writeUp(seriesA, seriesB, correlation, bestLagDays, pValue),
      stats: [
        { label: 'Correlation', value: shownCorrelation },
        { label: 'Best lag', value: formatLag(bestLagDays) },
        { label: 'p-value', value: formatP(pValue) },
        { label: 'Sample', value: `${N_DAYS} days` },
      ],
    },
  }
}
