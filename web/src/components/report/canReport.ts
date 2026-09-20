import type { Mission } from '../../types'

const DEVIN_KINDS = new Set(['thought', 'step', 'artifact', 'conclusion'])

/** A report needs something from Devin to look back on, and a failed mission only has that if it concluded first. */
export function canReport({ status, events }: Pick<Mission, 'status' | 'events'>): boolean {
  if (status === 'failed') return events.some((e) => e.kind === 'conclusion')
  return events.some((e) => DEVIN_KINDS.has(e.kind))
}
