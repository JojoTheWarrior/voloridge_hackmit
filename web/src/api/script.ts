import type { Mission, MissionEvent } from '../types'
import { buildFindings, type FindingsShape } from './findings'

export type Beat =
  | { kind: 'thought'; text: string }
  | { kind: 'step'; stepId: string; label: string }
  | { kind: 'artifact' }
  | { kind: 'conclusion' }

/** One scripted research run. Every beat adds exactly one event, so progress can be read off the thread. */
export const SCRIPT: Beat[] = [
  { kind: 'step', stepId: 's1', label: 'Read the linked datasets' },
  { kind: 'thought', text: 'Both sources cover the same window, so I can line them up day by day.' },
  { kind: 'step', stepId: 's2', label: 'Align the two series' },
  { kind: 'step', stepId: 's3', label: 'Test the relationship at each lag' },
  { kind: 'thought', text: 'One lag stands out from the rest. I am checking it against shuffled data before I trust it.' },
  { kind: 'artifact' },
  { kind: 'conclusion' },
]

export const REPLY_TEXT = 'Good question. I reran the test with that in mind and the result holds.'
export const REPLY_BEAT: Beat = { kind: 'thought', text: REPLY_TEXT }

type EventBody = MissionEvent extends infer E ? (E extends MissionEvent ? Omit<E, 'id' | 'at'> : never) : never

type Thread = Pick<Mission, 'hypothesis' | 'events' | 'updatedAt'>

function bodyOf(mission: Thread, beat: Beat, shape?: FindingsShape): EventBody {
  switch (beat.kind) {
    case 'thought':
      return beat
    case 'step':
      return { ...beat, state: 'active' }
    case 'artifact':
      return { kind: 'artifact', artifact: buildFindings(mission.hypothesis, shape).chart }
    case 'conclusion':
      return { kind: 'conclusion', ...buildFindings(mission.hypothesis, shape).conclusion }
  }
}

/** Plays one beat into the mission's thread, in place. */
export function applyBeat(mission: Thread, beat: Beat, at: string, shape?: FindingsShape) {
  if (beat.kind === 'step' || beat.kind === 'conclusion') {
    mission.events = mission.events.map((e) => (e.kind === 'step' && e.state === 'active' ? { ...e, state: 'done' } : e))
  }
  mission.events.push({ id: `e${mission.events.length + 1}`, at, ...bodyOf(mission, beat, shape) })
  mission.updatedAt = at
}

const MINUTE_MS = 60_000

/** The thread of a mission that asked its question at `startedAt` and has played `count` beats, a minute apart. */
export function threadAt(hypothesis: string, count: number, startedAt: string, shape?: FindingsShape): MissionEvent[] {
  const thread: Thread = { hypothesis, updatedAt: startedAt, events: [{ id: 'e1', at: startedAt, kind: 'user_message', text: hypothesis }] }
  SCRIPT.slice(0, count).forEach((beat, i) => {
    applyBeat(thread, beat, new Date(Date.parse(startedAt) + (i + 1) * MINUTE_MS).toISOString(), shape)
  })
  return thread.events
}
