import { buildResult, EXAMPLE_PROMPTS, seedDatasets, seedMissions } from './fixtures'

describe('buildResult', () => {
  it('is deterministic per hypothesis', () => {
    expect(buildResult('A leads B')).toEqual(buildResult('A leads B'))
    expect(buildResult('A leads B').points).not.toEqual(buildResult('C leads D').points)
  })

  it('produces a consistent daily series', () => {
    const { points, n, correlation, pValue, bestLagDays } = buildResult('A leads B')
    expect(points).toHaveLength(n)
    expect(points.at(-1)?.date).toBe('2026-09-15')
    expect(new Set(points.map((p) => p.date)).size).toBe(n)
    expect(Math.abs(correlation)).toBeLessThanOrEqual(1)
    expect(pValue).toBeGreaterThanOrEqual(0)
    expect(pValue).toBeLessThanOrEqual(1)
    expect(bestLagDays).toBeGreaterThanOrEqual(0)
  })

  it('reports a strong planted link as significant, with the right sign', () => {
    const positive = buildResult('x', { strength: 0.7, lagDays: 2 })
    expect(positive.correlation).toBeGreaterThan(0.4)
    expect(positive.pValue).toBeLessThan(0.05)
    expect(positive.verdict).not.toBe('No reliable link.')
    expect(buildResult('x', { strength: -0.7 }).correlation).toBeLessThan(-0.4)
  })

  it('names series from the hypothesis, falling back to generic names', () => {
    expect(buildResult('Do protest events move gold futures?')).toMatchObject({ seriesA: 'Protest events', seriesB: 'Gold futures' })
    expect(buildResult('something vague')).toMatchObject({ seriesA: 'Signal', seriesB: 'Target' })
  })
})

describe('seeds', () => {
  const missions = seedMissions()

  it('have unique ids and only reference known datasets', () => {
    expect(new Set(missions.map((m) => m.id)).size).toBe(missions.length)
    const known = new Set(seedDatasets().map((d) => d.id))
    missions.flatMap((m) => m.datasetIds).forEach((id) => expect(known).toContain(id))
  })

  it('include an honest null result alongside real links', () => {
    const verdicts = missions.filter((m) => m.status === 'done').map((m) => m.result?.verdict)
    expect(verdicts).toContain('No reliable link.')
    expect(verdicts.filter((v) => v !== 'No reliable link.').length).toBeGreaterThanOrEqual(3)
  })

  it('give done missions a result, failed missions an error, running missions neither', () => {
    for (const m of missions) {
      expect(Boolean(m.result)).toBe(m.status === 'done')
      expect(Boolean(m.error)).toBe(m.status === 'failed')
    }
  })

  it('offer three example prompts', () => {
    expect(EXAMPLE_PROMPTS).toHaveLength(3)
  })
})
