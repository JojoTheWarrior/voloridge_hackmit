import { stepsAt } from '../steps'
import type { Dataset, Mission, MissionResult, SeriesPoint } from '../types'

const N_DAYS = 120
const MAX_LAG = 7
const END_DATE = Date.UTC(2026, 8, 15)
const DAY_MS = 86_400_000
// Daily series are autocorrelated, so far fewer than N_DAYS observations are independent.
const EFFECTIVE_N = N_DAYS / 4

export const EXAMPLE_PROMPTS = [
  'Does wind speed in Tehran predict PM2.5 in Dubai two days later?',
  'Do protest events in Iran move gold futures?',
  'Does a Houston heat anomaly lead Henry Hub gas prices?',
]

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

function seriesNames(hypothesis: string): [string, string] {
  const match = hypothesis.match(
    /^(?:do|does|did|is|are|can)\s+(.+?)\s+(?:vs\.?|versus|leads?|predicts?|moves?|drives?|affects?|tracks?)\s+(.+?)\??$/i,
  )
  if (!match) return ['Signal', 'Target']
  const capitalize = (s: string) => s[0].toUpperCase() + s.slice(1)
  return [capitalize(match[1]), capitalize(match[2])]
}

function writeUp(a: string, b: string, r: number, lag: number, p: number): Pick<MissionResult, 'note' | 'verdict'> {
  const caveat = `This is a correlation over ${N_DAYS} days, not a causal claim. A shared driver could explain both series.`
  if (p >= 0.05 || Math.abs(r) < 0.2) {
    return {
      note: `${a} and ${b} show no dependable relationship at any lag up to ${MAX_LAG} days. The strongest correlation found was ${r.toFixed(2)}, which a permutation test cannot tell apart from chance.\n\nA null result is still a result: this pairing can be dropped from the queue.`,
      verdict: 'No reliable link.',
    }
  }
  const direction = r > 0 ? 'move together' : 'move in opposite directions'
  const timing = lag === 0 ? 'on the same day' : `with ${a} leading by ${lag} ${lag === 1 ? 'day' : 'days'}`
  return {
    note: `${a} and ${b} ${direction}, ${timing}. The link holds up under a permutation test, so it is unlikely to be chance.\n\n${caveat}`,
    verdict: Math.abs(r) >= 0.5 ? 'A strong link.' : 'A real but modest link.',
  }
}

interface ResultShape {
  seriesA?: string
  seriesB?: string
  /** Target correlation at the true lag, -1 to 1. */
  strength?: number
  lagDays?: number
}

/** Deterministic mock result: the same hypothesis always yields the same chart and stats. */
export function buildResult(hypothesis: string, shape: ResultShape = {}): MissionResult {
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

  let bestLagDays = 0
  let correlation = 0
  for (let lag = 0; lag <= MAX_LAG; lag++) {
    const r = pearson(a.slice(MAX_LAG - lag, length - lag), b.slice(MAX_LAG))
    if (Math.abs(r) > Math.abs(correlation)) [bestLagDays, correlation] = [lag, r]
  }

  const points: SeriesPoint[] = []
  for (let i = MAX_LAG; i < length; i++) {
    const date = new Date(END_DATE - (length - 1 - i) * DAY_MS).toISOString().slice(0, 10)
    points.push({ date, a: Number(a[i].toFixed(3)), b: Number(b[i].toFixed(3)) })
  }

  const pValue = pValueFor(correlation, EFFECTIVE_N)
  return {
    seriesA,
    seriesB,
    points,
    correlation: Number(correlation.toFixed(2)),
    bestLagDays,
    pValue: Number(pValue.toFixed(4)),
    n: N_DAYS,
    ...writeUp(seriesA, seriesB, correlation, bestLagDays, pValue),
  }
}

export function seedDatasets(now: number = Date.now()): Dataset[] {
  const hoursAgo = (h: number) => new Date(now - h * 3_600_000).toISOString()
  return [
    { id: 'gdelt', name: 'GDELT events', url: 'https://www.gdeltproject.org', seriesCount: 42, dateRange: 'Mar 2025 – Sep 2026', syncedAt: hoursAgo(2) },
    { id: 'yahoo', name: 'Yahoo Finance', url: 'https://finance.yahoo.com', seriesCount: 31, dateRange: 'Jan 2024 – Sep 2026', syncedAt: hoursAgo(2) },
    { id: 'open-meteo', name: 'Open-Meteo weather', url: 'https://open-meteo.com', seriesCount: 18, dateRange: 'Jan 2024 – Sep 2026', syncedAt: hoursAgo(26) },
    { id: 'cams', name: 'CAMS air quality', url: 'https://atmosphere.copernicus.eu', seriesCount: 12, dateRange: 'Jun 2024 – Sep 2026', syncedAt: hoursAgo(30) },
  ]
}

function done(
  id: string,
  title: string,
  hypothesis: string,
  createdAt: string,
  elapsedSeconds: number,
  datasetIds: string[],
  shape: ResultShape,
): Mission {
  return { id, title, hypothesis, status: 'done', datasetIds, createdAt, elapsedSeconds, steps: stepsAt(), result: buildResult(hypothesis, shape) }
}

export function seedMissions(): Mission[] {
  return [
    {
      id: 'tanker-brent',
      title: 'Tanker chatter vs Brent range',
      hypothesis: "Does tanker coverage in the news lead Brent's daily trading range?",
      status: 'running',
      datasetIds: ['gdelt', 'yahoo'],
      createdAt: '2026-09-20T11:52:00Z',
      elapsedSeconds: 141,
      steps: stepsAt('test'),
    },
    {
      id: 'tehran-wind-pm25',
      title: 'Tehran wind vs PM2.5',
      hypothesis: 'Does maximum wind speed in Tehran predict PM2.5 the next day?',
      status: 'running',
      datasetIds: ['open-meteo', 'cams'],
      createdAt: '2026-09-20T11:47:00Z',
      elapsedSeconds: 38,
      steps: stepsAt('pull'),
    },
    done('iran-events-brent', 'Iran events vs Brent returns', 'Do GDELT event counts for Iran lead Brent crude log returns?', '2026-09-20T10:31:00Z', 252, ['gdelt', 'yahoo'], { seriesA: 'Iran event count', seriesB: 'Brent log return', strength: 0.42, lagDays: 3 }),
    done('goldstein-vix', 'Goldstein tone vs VIX', 'Does the Goldstein tone of Iran coverage move the VIX?', '2026-09-20T09:58:00Z', 318, ['gdelt', 'yahoo'], { seriesA: 'Goldstein tone', seriesB: 'VIX close', strength: -0.5, lagDays: 1 }),
    done('houston-heat-gas', 'Houston heat vs Henry Hub gas', 'Does a Houston temperature anomaly lead Henry Hub natural gas prices?', '2026-09-20T09:12:00Z', 287, ['open-meteo', 'yahoo'], { seriesA: 'Houston temp anomaly', seriesB: 'Henry Hub spot', strength: 0.62, lagDays: 2 }),
    done('dubai-no2-brent', 'Dubai NO2 vs Brent', 'Does nitrogen dioxide over Dubai track the Brent crude price?', '2026-09-20T08:40:00Z', 231, ['cams', 'yahoo'], { seriesA: 'Dubai NO2', seriesB: 'Brent spot', strength: 0.02, lagDays: 0 }),
    done('protest-gold', 'Protest events vs gold', 'Do protest events in Iran move gold futures?', '2026-09-20T08:05:00Z', 264, ['gdelt', 'yahoo'], { seriesA: 'Iran protest events', seriesB: 'Gold log return', strength: 0.33, lagDays: 1 }),
    {
      id: 'houston-air',
      title: 'Houston air quality vs Gulf Coast',
      hypothesis: 'Does air quality along the US Gulf Coast follow Houston refinery activity?',
      status: 'failed',
      datasetIds: ['cams'],
      createdAt: '2026-09-20T07:30:00Z',
      elapsedSeconds: 44,
      steps: stepsAt('pull'),
      error: 'No air-quality series found for the US Gulf Coast.',
    },
  ]
}
