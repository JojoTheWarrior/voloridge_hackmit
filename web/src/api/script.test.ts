import { makeMission } from '../test/missions'
import type { Mission } from '../types'
import { applyBeat, REPLY_BEAT, SCRIPT, threadAt } from './script'

function blank(): Mission {
  return makeMission('working', { hypothesis: 'A leads B', events: [] })
}

function play(mission: Mission, count: number) {
  SCRIPT.slice(0, count).forEach((beat, i) => applyBeat(mission, beat, `2026-09-20T12:0${i}:00Z`))
  return mission
}

describe('script', () => {
  it('ends with the conclusion, after at least one step, thought and artifact', () => {
    expect(SCRIPT.at(-1)).toEqual({ kind: 'conclusion' })
    expect(new Set(SCRIPT.map((b) => b.kind))).toEqual(new Set(['step', 'thought', 'artifact', 'conclusion']))
  })

  it('adds exactly one event per beat, with unique ids, stamped with the time given', () => {
    const mission = blank()
    SCRIPT.forEach((beat, i) => {
      applyBeat(mission, beat, `2026-09-20T12:0${i}:00Z`)
      expect(mission.events).toHaveLength(i + 1)
      expect(mission.events[i].at).toBe(`2026-09-20T12:0${i}:00Z`)
      expect(mission.updatedAt).toBe(`2026-09-20T12:0${i}:00Z`)
    })
    expect(new Set(mission.events.map((e) => e.id)).size).toBe(SCRIPT.length)
  })

  it('keeps one step active at a time, finishing it in place when the next starts', () => {
    const mission = blank()
    SCRIPT.forEach((beat, i) => {
      applyBeat(mission, beat, '2026-09-20T12:00:00Z')
      const active = mission.events.filter((e) => e.kind === 'step' && e.state === 'active')
      expect(active.length).toBe(i === SCRIPT.length - 1 ? 0 : 1)
    })
    const steps = mission.events.filter((e) => e.kind === 'step')
    expect(new Set(steps.map((s) => s.stepId)).size).toBe(steps.length)
  })

  it('derives the artifact and conclusion from the hypothesis', () => {
    const a = play(blank(), SCRIPT.length)
    const b = play(blank(), SCRIPT.length)
    expect(a.events.filter((e) => e.kind === 'artifact')).toEqual(b.events.filter((e) => e.kind === 'artifact'))
    const conclusion = a.events.at(-1)
    expect(conclusion?.kind).toBe('conclusion')
    expect(conclusion?.kind === 'conclusion' && conclusion.stats.length).toBe(4)
  })

  it('shows each figure once, and every artifact has its own id', () => {
    const artifacts = play(blank(), SCRIPT.length).events.flatMap((e) => (e.kind === 'artifact' ? [e.artifact] : []))
    expect(artifacts.map((a) => a.type)).toEqual(['chart', 'chart', 'table'])
    expect(new Set(artifacts.map((a) => a.id)).size).toBe(3)
  })

  it('still has the mission testing lags four beats in, before any figure', () => {
    const mission = play(blank(), 4)
    expect(mission.events.at(-1)).toMatchObject({ kind: 'step', state: 'active' })
    expect(mission.events.some((e) => e.kind === 'artifact')).toBe(false)
  })

  it('honours a planted shape', () => {
    const mission = blank()
    SCRIPT.forEach((beat) => applyBeat(mission, beat, '2026-09-20T12:00:00Z', { strength: 0.02, lagDays: 0 }))
    expect(mission.events.at(-1)).toMatchObject({ kind: 'conclusion', verdict: 'No reliable link.' })
  })

  it('replies with a thought', () => {
    const mission = play(blank(), SCRIPT.length)
    applyBeat(mission, REPLY_BEAT, '2026-09-20T13:00:00Z')
    expect(mission.events.at(-1)).toMatchObject({ kind: 'thought', at: '2026-09-20T13:00:00Z' })
    expect(new Set(mission.events.map((e) => e.id)).size).toBe(mission.events.length)
  })
})

describe('threadAt', () => {
  it('opens with the hypothesis and spaces beats a minute apart', () => {
    const events = threadAt('A leads B', 2, '2026-09-20T12:00:00.000Z')
    expect(events.map((e) => e.kind)).toEqual(['user_message', 'step', 'thought'])
    expect(events[0]).toMatchObject({ text: 'A leads B', at: '2026-09-20T12:00:00.000Z' })
    expect(events.map((e) => e.at)).toEqual(['2026-09-20T12:00:00.000Z', '2026-09-20T12:01:00.000Z', '2026-09-20T12:02:00.000Z'])
  })

  it('stops at the end of the script', () => {
    expect(threadAt('A leads B', 99, '2026-09-20T12:00:00Z')).toHaveLength(SCRIPT.length + 1)
    expect(threadAt('A leads B', 0, '2026-09-20T12:00:00Z')).toHaveLength(1)
  })
})
