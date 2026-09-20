import { makeMission } from '../test/missions'
import type { MissionEvent } from '../types'
import { buildReport } from './report'
import { SCRIPT, threadAt } from './script'

const at = '2026-09-20T12:00:00.000Z'
const artifactIds = (events: MissionEvent[]) => events.flatMap((e) => (e.kind === 'artifact' ? [e.artifact.id] : []))

describe('buildReport', () => {
  it('states the finding, not the question, and stamps the time given', () => {
    const mission = makeMission('done', { hypothesis: 'Does wind lead dust?' })
    const report = buildReport(mission, at)
    expect(report.headline).toMatch(/^Wind /)
    expect(report.headline).not.toContain('?')
    expect(report.generatedAt).toBe(at)
  })

  it('carries the conclusion through: its stats, and its finding as the opening of the summary', () => {
    const mission = makeMission('done')
    const conclusion = mission.events.find((e) => e.kind === 'conclusion')
    const report = buildReport(mission, at)
    expect(conclusion?.kind === 'conclusion' && report.stats).toEqual(conclusion?.kind === 'conclusion' && conclusion.stats)
    expect(conclusion?.kind === 'conclusion' && report.summary.startsWith(conclusion.summary.split('\n')[0])).toBe(true)
    expect(report.summary).not.toContain('\n')
  })

  it('features only artifacts from the thread, at most three, in thread order', () => {
    const mission = makeMission('done')
    expect(buildReport(mission, at).keyArtifactIds).toEqual(artifactIds(mission.events).slice(0, 3))
    expect(buildReport(makeMission('failed'), at).keyArtifactIds).toEqual([])
  })

  it('retells every step with a takeaway', () => {
    const mission = makeMission('done')
    const labels = mission.events.flatMap((e) => (e.kind === 'step' ? [e.label] : []))
    const { steps } = buildReport(mission, at)
    expect(steps.map((s) => s.label)).toEqual(labels)
    steps.forEach((s) => expect(s.takeaway).not.toBe(''))
  })

  it('stays within the limits of the contract', () => {
    const report = buildReport(makeMission('done'), at)
    expect(report.stats.length).toBeLessThanOrEqual(4)
    expect(report.steps.length).toBeLessThanOrEqual(8)
    expect(report.caveats.length).toBeGreaterThan(0)
    expect(report.caveats.length).toBeLessThanOrEqual(4)
    expect(report.nextQuestions.length).toBeGreaterThan(0)
    expect(report.nextQuestions.length).toBeLessThanOrEqual(3)
  })

  it('is deterministic, and words the summary differently from the report it replaces', () => {
    const mission = makeMission('done')
    const first = buildReport(mission, at)
    expect(buildReport(mission, at)).toEqual(first)
    const second = buildReport({ ...mission, report: first }, at)
    expect(second.summary).not.toBe(first.summary)
    expect(second.headline).toBe(first.headline)
    const third = buildReport({ ...mission, report: second }, at)
    expect(third.summary).not.toBe(second.summary)
  })

  it('reports on work in progress when there is no conclusion yet', () => {
    const report = buildReport(makeMission('working', { title: 'Wind vs dust' }), at)
    expect(report.headline).toBe('Wind vs dust: no conclusion yet')
    expect(report.summary).not.toBe('')
    expect(report.stats).toEqual([])
  })

  it('says so plainly when the link is not there', () => {
    const events = threadAt('Does wind lead dust?', SCRIPT.length, at, { strength: 0.02, lagDays: 0 })
    expect(buildReport(makeMission('done', { events }), at).headline).toBe('Wind and Dust show no dependable relationship at any lag up to 7 days')
  })

  it('does not cut a headline at a decimal point', () => {
    const events = threadAt('Does wind predict PM2.5?', SCRIPT.length, at, { strength: 0.7, lagDays: 2 })
    expect(buildReport(makeMission('done', { events }), at).headline).toBe('Wind leads PM2.5 by 2 days')
  })
})
