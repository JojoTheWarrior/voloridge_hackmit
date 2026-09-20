import { makeMission } from '../../test/missions'
import type { MissionEvent } from '../../types'
import { foldWork } from './foldWork'

const at = '2026-09-20T12:00:00Z'
const kinds = (events: MissionEvent[]) => events.map((e) => e.kind)

describe('foldWork', () => {
  it('folds a done mission between its opening question and its conclusion', () => {
    const mission = makeMission('done')
    const { opening, work, rest } = foldWork(mission)
    expect(kinds(opening)).toEqual(['user_message'])
    expect(kinds(rest)).toEqual(['conclusion'])
    expect([...opening, ...work, ...rest]).toEqual(mission.events)
    expect(work.length).toBeGreaterThan(0)
  })

  it.each(['working', 'waiting', 'failed'] as const)('folds nothing while a mission is %s', (status) => {
    const mission = makeMission(status)
    expect(foldWork(mission)).toEqual({ opening: [], work: [], rest: mission.events })
  })

  it('folds nothing when a done mission never reached a conclusion', () => {
    const mission = makeMission('done', { events: makeMission('failed').events })
    expect(foldWork(mission)).toEqual({ opening: [], work: [], rest: mission.events })
  })

  it('keeps what came after the conclusion in view', () => {
    const mission = makeMission('done')
    const later: MissionEvent[] = [
      { id: 'u2', at, kind: 'user_message', text: 'And weekends?' },
      { id: 't2', at, kind: 'thought', text: 'Same result.' },
    ]
    mission.events.push(...later)
    expect(kinds(foldWork(mission).rest)).toEqual(['conclusion', 'user_message', 'thought'])
  })

  it('folds from the top when the thread does not open with the question', () => {
    const events: MissionEvent[] = [
      { id: 't1', at, kind: 'thought', text: 'Starting.' },
      { id: 'c1', at, kind: 'conclusion', verdict: 'No reliable link.', summary: '', stats: [] },
    ]
    const { opening, work } = foldWork(makeMission('done', { events }))
    expect(opening).toEqual([])
    expect(kinds(work)).toEqual(['thought'])
  })

  it('has no work to fold when the conclusion follows the question directly', () => {
    const events: MissionEvent[] = [
      { id: 'u1', at, kind: 'user_message', text: 'Does A lead B?' },
      { id: 'c1', at, kind: 'conclusion', verdict: 'No reliable link.', summary: '', stats: [] },
    ]
    expect(foldWork(makeMission('done', { events })).work).toEqual([])
  })

  it('keeps a report that follows the conclusion in view', () => {
    const mission = makeMission('done')
    mission.events.push({ id: 'report', at, kind: 'report' })
    const { work, rest } = foldWork(mission)
    expect(kinds(rest)).toEqual(['conclusion', 'report'])
    expect(kinds(work)).not.toContain('report')
  })

  it('lifts a report written before the conclusion out of the fold, to just after the conclusion', () => {
    const mission = makeMission('done')
    const conclusion = mission.events.pop()!
    mission.events.push({ id: 'report', at, kind: 'report' }, conclusion, { id: 'u2', at, kind: 'user_message', text: 'Thanks' })
    const { opening, work, rest } = foldWork(mission)
    expect(kinds(rest)).toEqual(['conclusion', 'report', 'user_message'])
    expect(kinds(work)).not.toContain('report')
    expect(opening.length + work.length + rest.length).toBe(mission.events.length)
  })

  it('leaves a report where it is while nothing is folded', () => {
    const mission = makeMission('waiting')
    mission.events.splice(2, 0, { id: 'report', at, kind: 'report' })
    expect(foldWork(mission).rest).toEqual(mission.events)
  })
})
