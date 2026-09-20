import type { Dataset, Mission, MissionStatus } from '../types'
import type { FindingsShape } from './findings'
import { SCRIPT, threadAt } from './script'
import { HOUSTON_REPORT, type ReportText } from './seedReport'

export function seedDatasets(now: number = Date.now()): Dataset[] {
  const hoursAgo = (h: number) => new Date(now - h * 3_600_000).toISOString()
  return [
    { id: 'gdelt', kind: 'events', name: 'GDELT events', url: 'https://www.gdeltproject.org', seriesCount: 42, dateRange: 'Mar 2025 – Sep 2026', syncedAt: hoursAgo(2) },
    { id: 'yahoo', kind: 'markets', name: 'Yahoo Finance', url: 'https://finance.yahoo.com', seriesCount: 31, dateRange: 'Jan 2024 – Sep 2026', syncedAt: hoursAgo(2) },
    { id: 'open-meteo', kind: 'weather', name: 'Open-Meteo weather', url: 'https://open-meteo.com', seriesCount: 18, dateRange: 'Jan 2024 – Sep 2026', syncedAt: hoursAgo(26) },
    { id: 'cams', kind: 'air', name: 'CAMS air quality', url: 'https://atmosphere.copernicus.eu', seriesCount: 12, dateRange: 'Jun 2024 – Sep 2026', syncedAt: hoursAgo(30) },
  ]
}

interface Seed {
  id: string
  title: string
  hypothesis: string
  status: MissionStatus
  createdAt: string
  datasetIds: string[]
  /** How far through the script the mission has got; settled missions have played all of it. */
  beats?: number
  shape?: FindingsShape
  needsUser?: string
  error?: string
  report?: ReportText
}

// Devin was asked for the report a few minutes after it concluded.
const REPORT_DELAY_MS = 4 * 60_000

const SEEDS: Seed[] = [
  { id: 'tanker-brent', title: 'Tanker chatter vs Brent range', hypothesis: "Does tanker coverage in the news lead Brent's daily trading range?", status: 'working', createdAt: '2026-09-20T11:52:00Z', datasetIds: ['gdelt', 'yahoo'], beats: 4 },
  { id: 'tehran-wind-pm25', title: 'Tehran wind vs PM2.5', hypothesis: 'Does maximum wind speed in Tehran predict PM2.5 the next day?', status: 'working', createdAt: '2026-09-20T11:47:00Z', datasetIds: ['open-meteo', 'cams'], beats: 2 },
  { id: 'iran-events-brent', title: 'Iran events vs Brent returns', hypothesis: 'Do GDELT event counts for Iran lead Brent crude log returns?', status: 'done', createdAt: '2026-09-20T10:31:00Z', datasetIds: ['gdelt', 'yahoo'], shape: { seriesA: 'Iran event count', seriesB: 'Brent log return', strength: 0.42, lagDays: 3 } },
  { id: 'goldstein-vix', title: 'Goldstein tone vs VIX', hypothesis: 'Does the Goldstein tone of Iran coverage move the VIX?', status: 'done', createdAt: '2026-09-20T09:58:00Z', datasetIds: ['gdelt', 'yahoo'], shape: { seriesA: 'Goldstein tone', seriesB: 'VIX close', strength: -0.5, lagDays: 1 } },
  { id: 'houston-heat-gas', title: 'Houston heat vs Henry Hub gas', hypothesis: 'Does a Houston temperature anomaly lead Henry Hub natural gas prices?', status: 'done', createdAt: '2026-09-20T09:12:00Z', datasetIds: ['open-meteo', 'yahoo'], shape: { seriesA: 'Houston temp anomaly', seriesB: 'Henry Hub spot', strength: 0.62, lagDays: 2 }, report: HOUSTON_REPORT },
  { id: 'dubai-no2-brent', title: 'Dubai NO2 vs Brent', hypothesis: 'Does nitrogen dioxide over Dubai track the Brent crude price?', status: 'done', createdAt: '2026-09-20T08:40:00Z', datasetIds: ['cams', 'yahoo'], shape: { seriesA: 'Dubai NO2', seriesB: 'Brent spot', strength: 0.02, lagDays: 0 } },
  { id: 'protest-gold', title: 'Protest events vs gold', hypothesis: 'Do protest events in Iran move gold futures?', status: 'waiting', createdAt: '2026-09-20T08:05:00Z', datasetIds: ['gdelt', 'yahoo'], shape: { seriesA: 'Iran protest events', seriesB: 'Gold log return', strength: 0.33, lagDays: 1 }, needsUser: 'The link is too weak to call either way. Should I extend the window to two years and rerun?' },
  { id: 'houston-air', title: 'Houston air quality vs Gulf Coast', hypothesis: 'Does air quality along the US Gulf Coast follow Houston refinery activity?', status: 'failed', createdAt: '2026-09-20T07:30:00Z', datasetIds: ['cams'], beats: 1, error: 'No air-quality series found for the US Gulf Coast.' },
]

export function seedMissions(): Mission[] {
  return SEEDS.map(({ beats = SCRIPT.length, shape, error, report: text, ...mission }) => {
    const createdAt = new Date(mission.createdAt).toISOString()
    const events = threadAt(mission.hypothesis, beats, createdAt, shape)
    if (error) events.push({ id: `e${events.length + 1}`, at: events.at(-1)!.at, kind: 'error', text: error })
    const seeded: Mission = { ...mission, createdAt, updatedAt: events.at(-1)!.at, reportPending: false, events }
    if (!text) return seeded
    const conclusion = events.findLast((e) => e.kind === 'conclusion')
    const generatedAt = new Date(Date.parse(seeded.updatedAt) + REPORT_DELAY_MS).toISOString()
    events.push({ id: 'report', at: generatedAt, kind: 'report' })
    return { ...seeded, updatedAt: generatedAt, report: { ...text, stats: conclusion?.stats ?? [], generatedAt } }
  })
}
