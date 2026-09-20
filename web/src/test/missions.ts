import { SCRIPT, threadAt } from '../api/script'
import type { Explorer, Mission, MissionStatus, Report } from '../types'

let counter = 0

const BEATS_PLAYED: Record<MissionStatus, number> = { working: 4, waiting: SCRIPT.length, done: SCRIPT.length, failed: 1 }

/** A minimal mission for tests; working missions never tick unless timers are advanced. */
export function makeMission(status: MissionStatus, overrides: Partial<Mission> = {}): Mission {
  counter += 1
  const createdAt = overrides.createdAt ?? new Date(Date.UTC(2026, 0, 1, 0, counter)).toISOString()
  const hypothesis = overrides.hypothesis ?? `Hypothesis ${counter}`
  const events = threadAt(hypothesis, BEATS_PLAYED[status], createdAt)
  if (status === 'failed') events.push({ id: 'error', at: createdAt, kind: 'error', text: 'It broke.' })
  return {
    id: `t-${counter}`,
    title: `Mission ${counter}`,
    hypothesis,
    status,
    datasetIds: [],
    reportPending: false,
    explorerPending: false,
    createdAt,
    updatedAt: events.at(-1)!.at,
    events,
    ...overrides,
  }
}

/** A full report whose figures are the ones a settled `makeMission` thread contains. */
export function makeReport(overrides: Partial<Report> = {}): Report {
  return {
    headline: 'Wind leads dust by two days',
    summary: 'When the wind picks up, dust follows two days later. The link beats shuffled data.',
    stats: [
      { label: 'Correlation', value: '0.58' },
      { label: 'Best lag', value: '2 days' },
    ],
    keyArtifactIds: ['a1', 'a2'],
    steps: [
      { label: 'Read both datasets', takeaway: 'They cover the same window.' },
      { label: 'Test each lag', takeaway: 'Two days stands out.' },
    ],
    caveats: ['A correlation is not a causal claim.'],
    nextQuestions: ['Does it hold over two years?', 'Is there a weekday effect?'],
    generatedAt: '2026-09-20T12:30:00.000Z',
    ...overrides,
  }
}

export function makeExplorer(overrides: Partial<Explorer> = {}): Explorer {
  return {
    version: 1,
    title: 'Clinics by flood risk',
    description: 'Pan the map and select a clinic to see the evidence behind its score.',
    src: '/api/missions/m1/explorer/1/index.html',
    builtAt: '2026-09-20T12:40:00.000Z',
    ...overrides,
  }
}
