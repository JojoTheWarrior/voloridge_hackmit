import type { MissionStep, StepKey } from './types'

export const STEP_KEYS: StepKey[] = ['plan', 'pull', 'test', 'chart', 'writeup']

export const STEP_LABELS: Record<StepKey, { active: string; done: string }> = {
  plan: { active: 'Planning the test', done: 'Planned the test' },
  pull: { active: 'Pulling the data', done: 'Pulled the data' },
  test: { active: 'Running the permutation test', done: 'Ran the permutation test' },
  chart: { active: 'Drawing the chart', done: 'Drew the chart' },
  writeup: { active: 'Writing up the findings', done: 'Wrote up the findings' },
}

/** Steps for a mission whose `active` step is in flight; omit it for a finished mission. */
export function stepsAt(active?: StepKey): MissionStep[] {
  const activeIndex = active ? STEP_KEYS.indexOf(active) : STEP_KEYS.length
  return STEP_KEYS.map((key, i) => ({
    key,
    label: STEP_LABELS[key].done,
    state: i < activeIndex ? 'done' : i === activeIndex ? 'active' : 'pending',
  }))
}
