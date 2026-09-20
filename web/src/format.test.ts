import { formatElapsed, formatP, formatSynced } from './format'

describe('formatElapsed', () => {
  it.each([
    [0, '0s'],
    [59, '59s'],
    [60, '1m 0s'],
    [252, '4m 12s'],
    [3599, '59m 59s'],
    [3600, '1h 0m'],
    [7384, '2h 3m'],
  ])('%i seconds -> %s', (seconds, expected) => {
    expect(formatElapsed(seconds)).toBe(expected)
  })

  it('rounds fractional seconds', () => {
    expect(formatElapsed(12.6)).toBe('13s')
  })
})

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
