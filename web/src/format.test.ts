import { formatCorrelation, formatLag, formatP, formatSynced } from './format'

describe('formatP', () => {
  it.each([
    [0.0004, '<0.001'],
    [0.001, '0.001'],
    [0.002, '0.002'],
    [0.5, '0.500'],
    [1, '1.000'],
  ])('%f -> %s', (p, expected) => {
    expect(formatP(p)).toBe(expected)
  })
})

describe('formatSynced', () => {
  const now = new Date('2026-09-20T12:00:00Z')
  const ago = (ms: number) => new Date(now.getTime() - ms).toISOString()

  it.each([
    [30_000, 'just now'],
    [5 * 60_000, '5m ago'],
    [2 * 3_600_000, '2h ago'],
    [26 * 3_600_000, '1d ago'],
    [9 * 86_400_000, '9d ago'],
  ])('%i ms ago -> %s', (ms, expected) => {
    expect(formatSynced(ago(ms), now)).toBe(expected)
  })

  it('treats future timestamps as just now', () => {
    expect(formatSynced(ago(-60_000), now)).toBe('just now')
  })
})

describe('formatCorrelation', () => {
  it.each([
    [0.414, '0.41'],
    [-0.5, '−0.50'],
    [0, '0.00'],
    [-0.001, '−0.00'],
  ])('%f -> %s', (r, expected) => {
    expect(formatCorrelation(r)).toBe(expected)
  })
})

describe('formatLag', () => {
  it.each([
    [0, 'Same day'],
    [1, '1 day'],
    [7, '7 days'],
  ])('%i -> %s', (days, expected) => {
    expect(formatLag(days)).toBe(expected)
  })
})
