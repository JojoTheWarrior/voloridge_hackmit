import type { Mission, MissionEvent } from '../../types'

interface Folded {
  /** The question that opened the thread; it stays in view. */
  opening: MissionEvent[]
  /** What goes behind the "Show the work" toggle. */
  work: MissionEvent[]
  rest: MissionEvent[]
}

/** Once a mission is done, everything between the opening question and the conclusion folds away, except a report: that is what people come back for. */
export function foldWork({ status, events }: Pick<Mission, 'status' | 'events'>): Folded {
  const conclusion = events.findLastIndex((e) => e.kind === 'conclusion')
  if (status !== 'done' || conclusion < 0) return { opening: [], work: [], rest: events }
  const start = events[0].kind === 'user_message' ? 1 : 0
  const before = events.slice(start, conclusion)
  return {
    opening: events.slice(0, start),
    work: before.filter((e) => e.kind !== 'report'),
    rest: [events[conclusion], ...before.filter((e) => e.kind === 'report'), ...events.slice(conclusion + 1)],
  }
}
