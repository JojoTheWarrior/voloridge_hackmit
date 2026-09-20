import { SCRIPT, threadAt } from '../api/script'
import type { Mission, MissionStatus } from '../types'

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
    createdAt,
    updatedAt: events.at(-1)!.at,
    events,
    ...overrides,
  }
}
