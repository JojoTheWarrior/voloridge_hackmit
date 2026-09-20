import type { Mission, MissionEvent } from '../../types'

interface Folded {
  /** The question that opened the thread; it stays in view. */
  opening: MissionEvent[]
  /** What goes behind the "Show the work" toggle. */
  work: MissionEvent[]
  rest: MissionEvent[]
}

/** Once a mission is done, everything between the opening question and the conclusion folds away. */
export function foldWork({ status, events }: Pick<Mission, 'status' | 'events'>): Folded {
  const conclusion = events.findLastIndex((e) => e.kind === 'conclusion')
  if (status !== 'done' || conclusion < 0) return { opening: [], work: [], rest: events }
  const start = events[0].kind === 'user_message' ? 1 : 0
  return { opening: events.slice(0, start), work: events.slice(start, conclusion), rest: events.slice(conclusion) }
}
