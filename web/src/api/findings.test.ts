import { formatCorrelation } from '../format'
import { buildFindings } from './findings'

const stat = (findings: ReturnType<typeof buildFindings>, label: string) =>
  findings.conclusion.stats.find((s) => s.label === label)?.value

describe('buildFindings', () => {
  it('is deterministic per hypothesis', () => {
    expect(buildFindings('A leads B')).toEqual(buildFindings('A leads B'))
    expect(buildFindings('A leads B').chart.series).not.toEqual(buildFindings('C leads D').chart.series)
  })

  it('charts two aligned daily series ending on the same date', () => {
    const { chart } = buildFindings('A leads B')
    expect(chart).toMatchObject({ type: 'chart', kind: 'line' })
    expect(chart.series).toHaveLength(2)
    const [a, b] = chart.series
    expect(a.points).toHaveLength(120)
    expect(b.points.map(([x]) => x)).toEqual(a.points.map(([x]) => x))
    expect(a.points.at(-1)?.[0]).toBe('2026-09-15')
    expect(new Set(a.points.map(([x]) => x)).size).toBe(120)
    a.points.forEach(([, y]) => expect(Number.isFinite(y)).toBe(true))
  })

  it('reports the core stats as display strings', () => {
    const findings = buildFindings('A leads B')
    expect(findings.conclusion.stats.map((s) => s.label)).toEqual(['Correlation', 'Best lag', 'p-value', 'Sample'])
    expect(stat(findings, 'Correlation')).toMatch(/^−?[01]\.\d\d$/)
    expect(stat(findings, 'Sample')).toBe('120 days')
    expect(findings.chart.headline).toBe(`r = ${stat(findings, 'Correlation')}`)
  })

  it('reports a strong planted link as significant, with the right sign', () => {
    const positive = buildFindings('x', { strength: 0.7, lagDays: 2 })
    expect(Number(stat(positive, 'Correlation'))).toBeGreaterThan(0.4)
    expect(stat(positive, 'Best lag')).toBe('2 days')
    expect(positive.conclusion.verdict).not.toBe('No reliable link.')
    expect(stat(buildFindings('x', { strength: -0.7 }), 'Correlation')).toMatch(/^−0\.[4-9]/)
  })

  it('calls a planted null a null', () => {
    expect(buildFindings('x', { strength: 0.02, lagDays: 0 }).conclusion.verdict).toBe('No reliable link.')
  })

  it('opens the summary with the leading series rather than naming it mid-sentence', () => {
    expect(buildFindings('x', { seriesA: 'Wind', seriesB: 'Dust', strength: 0.7, lagDays: 2 }).conclusion.summary).toMatch(
      /^Wind leads Dust by 2 days, and the two move together\./,
    )
    expect(buildFindings('x', { seriesA: 'Wind', seriesB: 'Dust', strength: -0.7, lagDays: 0 }).conclusion.summary).toMatch(
      /^Wind and Dust move in opposite directions on the same day\./,
    )
  })

  it('names series from the hypothesis, falling back to generic names', () => {
    expect(buildFindings('Do protest events move gold futures?').chart.series.map((s) => s.name)).toEqual(['Protest events', 'Gold futures'])
    expect(buildFindings('something vague').chart.series.map((s) => s.name)).toEqual(['Signal', 'Target'])
    expect(buildFindings('something vague').chart.title).toBe('Signal vs Target')
  })

  it('charts the correlation at every lag, peaking where the conclusion says', () => {
    const findings = buildFindings('x', { strength: 0.7, lagDays: 2 })
    expect(findings.lags).toMatchObject({ type: 'chart', kind: 'bar', headline: 'Best at 2 days' })
    const [sweep] = findings.lags.series
    expect(sweep.points.map(([x]) => x)).toEqual(['0', '1', '2', '3', '4', '5', '6', '7'])
    const best = sweep.points.reduce((a, b) => (Math.abs(b[1]) > Math.abs(a[1]) ? b : a))
    expect(best[0]).toBe('2')
    expect(formatCorrelation(best[1])).toBe(stat(findings, 'Correlation'))
  })

  it('tabulates robustness checks, the first being the headline correlation', () => {
    const findings = buildFindings('x', { strength: 0.7, lagDays: 2 })
    expect(findings.checks).toMatchObject({ type: 'table', columns: ['Check', 'Correlation', 'Holds'] })
    expect(findings.checks.rows.map((row) => row[0])).toEqual(['Full window', 'First half', 'Second half', 'Without the 5 largest moves'])
    expect(findings.checks.rows[0]).toEqual(['Full window', stat(findings, 'Correlation'), 'Yes'])
    findings.checks.rows.forEach((row) => expect(row[1]).toMatch(/^−?[01]\.\d\d$/))
  })

  it('says a null result does not hold', () => {
    const { checks } = buildFindings('x', { strength: 0.02, lagDays: 0 })
    expect(checks.rows[0][2]).toBe('No')
  })

  it('gives every figure its own id', () => {
    const { chart, lags, checks } = buildFindings('A leads B')
    expect(new Set([chart.id, lags.id, checks.id]).size).toBe(3)
  })
})
