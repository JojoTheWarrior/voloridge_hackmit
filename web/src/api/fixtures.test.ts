import type { Mission } from '../types'
import { seedDatasets, seedMissions } from './fixtures'

const conclusionOf = (mission: Mission) => mission.events.find((e) => e.kind === 'conclusion')

describe('seeds', () => {
  const missions = seedMissions()

  it('have unique ids and only reference known datasets', () => {
    expect(new Set(missions.map((m) => m.id)).size).toBe(missions.length)
    const known = new Set(seedDatasets().map((d) => d.id))
    missions.flatMap((m) => m.datasetIds).forEach((id) => expect(known).toContain(id))
  })

  it('cover every status', () => {
    expect(new Set(missions.map((m) => m.status))).toEqual(new Set(['working', 'waiting', 'done', 'failed']))
  })

  it('open every thread with the hypothesis and keep event ids unique', () => {
    for (const m of missions) {
      expect(m.events[0]).toMatchObject({ kind: 'user_message', text: m.hypothesis, at: m.createdAt })
      expect(new Set(m.events.map((e) => e.id)).size).toBe(m.events.length)
      expect(m.updatedAt).toBe(m.events.at(-1)?.at)
    }
  })

  it('include an honest null result alongside real links', () => {
    const verdicts = missions
      .filter((m) => m.status === 'done')
      .map(conclusionOf)
      .map((c) => c?.kind === 'conclusion' && c.verdict)
    expect(verdicts).toContain('No reliable link.')
    expect(verdicts.filter((v) => v !== 'No reliable link.').length).toBeGreaterThanOrEqual(3)
  })

  it('give settled missions a conclusion, failed missions an error, working missions neither', () => {
    for (const m of missions) {
      expect(Boolean(conclusionOf(m))).toBe(m.status === 'done' || m.status === 'waiting')
      expect(m.events.some((e) => e.kind === 'error')).toBe(m.status === 'failed')
      expect(m.events.some((e) => e.kind === 'step' && e.state === 'active')).toBe(m.status === 'working' || m.status === 'failed')
    }
  })

  it('start with no report pending', () => {
    missions.forEach((m) => expect(m.reportPending).toBe(false))
  })

  describe('the one finished report', () => {
    const reported = missions.filter((m) => m.report)
    const [mission] = reported
    const report = mission?.report

    it('belongs to a done mission and closes its thread', () => {
      expect(reported.map((m) => m.status)).toEqual(['done'])
      expect(missions.flatMap((m) => m.events).filter((e) => e.kind === 'report')).toHaveLength(1)
      expect(mission.events.at(-1)).toEqual({ id: 'report', at: report?.generatedAt, kind: 'report' })
      expect(Date.parse(report!.generatedAt)).toBeGreaterThan(Date.parse(mission.events.at(-2)!.at))
    })

    it('features artifacts from its own thread and repeats the numbers of its conclusion', () => {
      const ids = mission.events.flatMap((e) => (e.kind === 'artifact' ? [e.artifact.id] : []))
      expect(report?.keyArtifactIds.length).toBeGreaterThan(1)
      report?.keyArtifactIds.forEach((id) => expect(ids).toContain(id))
      const conclusion = conclusionOf(mission)
      expect(conclusion?.kind === 'conclusion' && conclusion.stats).toEqual(report?.stats)
    })

    it('quotes no correlation that the thread does not show', () => {
      const thread = JSON.stringify(mission.events)
      const prose = [report?.headline, report?.summary, ...report!.steps.map((s) => s.takeaway), ...report!.caveats].join(' ')
      const quoted = prose.match(/\b0\.\d\d\b/g) ?? []
      expect(quoted.length).toBeGreaterThan(0)
      quoted.forEach((number) => expect(thread).toContain(`"${number}"`))
    })

    it('retells the steps of the thread and stays within the contract limits', () => {
      const labels = mission.events.flatMap((e) => (e.kind === 'step' ? [e.label] : []))
      expect(report?.steps.map((s) => s.label)).toEqual(labels)
      expect(report?.stats.length).toBeLessThanOrEqual(4)
      expect(report?.keyArtifactIds.length).toBeLessThanOrEqual(3)
      expect(report?.caveats.length).toBeLessThanOrEqual(4)
      expect(report?.nextQuestions.length).toBeLessThanOrEqual(3)
    })
  })

  it('has the waiting mission ask the user something', () => {
    expect(missions.filter((m) => m.needsUser).map((m) => m.status)).toEqual(['waiting'])
  })

  it('tags each seed dataset with its kind', () => {
    expect(Object.fromEntries(seedDatasets().map((d) => [d.id, d.kind]))).toEqual({
      gdelt: 'events',
      yahoo: 'markets',
      'open-meteo': 'weather',
      cams: 'air',
    })
  })
})
