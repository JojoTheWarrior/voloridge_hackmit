import { stepsAt } from '../steps'
import type { Mission, MissionStatus } from '../types'

let counter = 0

/** A minimal mission for tests; running missions never tick unless timers are advanced. */
export function makeMission(status: MissionStatus, overrides: Partial<Mission> = {}): Mission {
  counter += 1
  return {
    id: `t-${counter}`,
    title: `Mission ${counter}`,
    hypothesis: `Hypothesis ${counter}`,
    status,
    datasetIds: [],
    createdAt: new Date(Date.UTC(2026, 0, 1, 0, counter)).toISOString(),
    elapsedSeconds: 252,
    steps: status === 'running' ? stepsAt('test') : status === 'failed' ? stepsAt('pull') : stepsAt(),
    ...(status === 'failed' ? { error: 'It broke.' } : {}),
    ...overrides,
  }
}
