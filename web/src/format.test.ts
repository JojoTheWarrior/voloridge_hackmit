import { formatCorrelation, formatElapsed, formatLag, formatP, formatReportDate, formatSynced, hostname, pluralize } from './format'

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

describe('formatElapsed', () => {
  const start = '2026-09-20T09:12:00Z'
  const after = (ms: number) => new Date(Date.parse(start) + ms).toISOString()
  const MINUTE = 60_000
  const HOUR = 60 * MINUTE

  it.each([
    [0, 'under a minute'],
    [59_999, 'under a minute'],
    [MINUTE, '1 minute'],
    [14 * MINUTE + 30_000, '14 minutes'],
    [59 * MINUTE, '59 minutes'],
    [HOUR, '1 hour'],
    [89 * MINUTE, '1 hour'],
    [90 * MINUTE, '2 hours'],
    [23 * HOUR, '23 hours'],
    [24 * HOUR, '1 day'],
    [36 * HOUR, '2 days'],
    [9 * 24 * HOUR, '9 days'],
  ])('%i ms -> %s', (ms, expected) => {
    expect(formatElapsed(start, after(ms))).toBe(expected)
  })

  it('treats an end before the start as under a minute', () => {
    expect(formatElapsed(start, after(-HOUR))).toBe('under a minute')
  })

  it.each([['nonsense', start], [start, ''], ['', '']])('has nothing to say about %j to %j', (from, to) => {
    expect(formatElapsed(from, to)).toBe('')
  })
})

describe('formatReportDate', () => {
  it.each([
    ['2026-09-20T12:00:00', '20 Sep 2026'],
    ['2026-01-01T12:00:00', '1 Jan 2026'],
    ['2025-12-31T12:00:00', '31 Dec 2025'],
  ])('%s -> %s', (iso, expected) => {
    expect(formatReportDate(iso)).toBe(expected)
  })

  it('has nothing to say about a date it cannot read', () => {
    expect(formatReportDate('soon')).toBe('')
  })
})

describe('pluralize', () => {
  it.each([
    [0, '0 steps'],
    [1, '1 step'],
    [2, '2 steps'],
  ])('%i -> %s', (count, expected) => {
    expect(pluralize(count, 'step')).toBe(expected)
  })
})

describe('hostname', () => {
  it('shows the source host without www or a path', () => {
    expect(hostname('https://www.gdeltproject.org/data')).toBe('gdeltproject.org')
  })
})
