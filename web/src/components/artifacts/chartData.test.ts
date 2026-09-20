import type { ChartArtifact } from '../../types'
import { buildChartModel, formatNumber, formatValue, seriesColor } from './chartData'
import { dateTicks, niceTicks } from './chartTicks'

const chart = (over: Partial<ChartArtifact>): ChartArtifact => ({
  id: 'a1',
  type: 'chart',
  kind: 'line',
  title: 'Chart',
  series: [],
  ...over,
})

describe('buildChartModel', () => {
  it('merges numeric series into rows sorted by x', () => {
    const model = buildChartModel(
      chart({
        series: [
          { name: 'A', points: [[2, 20], [1, 10]] },
          { name: 'B', points: [[1, 5], [3, 7]] },
        ],
      }),
    )
    expect(model.xMode).toBe('number')
    expect(model.rows).toEqual([
      { x: 1, s0: 10, s1: 5 },
      { x: 2, s0: 20 },
      { x: 3, s1: 7 },
    ])
    expect(model.series.map((s) => [s.key, s.name, s.count])).toEqual([
      ['s0', 'A', 2],
      ['s1', 'B', 2],
    ])
    expect(model.empty).toBe(false)
  })

  it('detects ISO dates, plots them as timestamps and formats ticks like "Jun 3"', () => {
    const model = buildChartModel(
      chart({ series: [{ name: 'A', points: [['2026-06-03', 1], ['2026-06-01', 2], ['2026-06-02T12:00:00Z', 3]] }] }),
    )
    expect(model.xMode).toBe('date')
    expect(model.rows.map((row) => row.x)).toEqual([
      Date.parse('2026-06-01'),
      Date.parse('2026-06-02T12:00:00Z'),
      Date.parse('2026-06-03'),
    ])
    expect(model.formatX(Date.parse('2026-06-03'))).toBe('Jun 3')
  })

  it('adds the year to date ticks when the range spans more than a year', () => {
    const model = buildChartModel(chart({ series: [{ name: 'A', points: [['2024-01-15', 1], ['2026-06-03', 2]] }] }))
    expect(model.formatX(Date.parse('2026-06-03'))).toBe('Jun 2026')
  })

  it('treats non-date strings as categories in first-seen order', () => {
    const model = buildChartModel(
      chart({
        kind: 'bar',
        series: [
          { name: 'A', points: [['West', 3], ['East', 1]] },
          { name: 'B', points: [['East', 4], ['North', 2]] },
        ],
      }),
    )
    expect(model.xMode).toBe('category')
    expect(model.rows).toEqual([
      { x: 0, s0: 3 },
      { x: 1, s0: 1, s1: 4 },
      { x: 2, s1: 2 },
    ])
    expect([0, 1, 2].map(model.formatX)).toEqual(['West', 'East', 'North'])
  })

  it('falls back to categories when x values mix numbers, dates and words', () => {
    const model = buildChartModel(chart({ series: [{ name: 'A', points: [[1, 1], ['2026-06-03', 2], ['later', 3]] }] }))
    expect(model.xMode).toBe('category')
    expect(model.rows.map((row) => model.formatX(row.x))).toEqual(['1', '2026-06-03', 'later'])
  })

  it('reads numeric strings as numbers when every x is numeric', () => {
    const model = buildChartModel(chart({ series: [{ name: 'A', points: [['2', 1], [1, 2]] }] }))
    expect(model.xMode).toBe('number')
    expect(model.rows.map((row) => row.x)).toEqual([1, 2])
  })

  it('always uses categories for bars, keeping the given order and formatting date labels', () => {
    const model = buildChartModel(chart({ kind: 'bar', series: [{ name: 'A', points: [['2026-06-03', 1], ['2026-06-01', 2]] }] }))
    expect(model.xMode).toBe('category')
    expect(model.rows.map((row) => model.formatX(row.x))).toEqual(['Jun 3', 'Jun 1'])
  })

  it('drops points with non-finite or malformed values', () => {
    const points = [[1, NaN], [Infinity, 2], [2, 5], [null, 1], [3], 'junk', [4, '7'], [5, null]] as unknown as [number, number][]
    const model = buildChartModel(chart({ series: [{ name: 'A', points }] }))
    expect(model.rows).toEqual([{ x: 2, s0: 5 }])
    expect(model.series[0].count).toBe(1)
  })

  it('is empty when there are no series, no points, or nothing valid', () => {
    expect(buildChartModel(chart({ series: [] })).empty).toBe(true)
    expect(buildChartModel(chart({ series: [{ name: 'A', points: [] }] })).empty).toBe(true)
    expect(buildChartModel(chart({ series: [{ name: 'A', points: [[NaN, NaN]] }] })).empty).toBe(true)
    expect(buildChartModel(chart({ series: undefined as unknown as [] })).empty).toBe(true)
    expect(buildChartModel(chart({ series: [null, { name: 'A' }] as unknown as [] })).empty).toBe(true)
  })

  it('drops series without valid points but keeps colors tied to the surviving order', () => {
    const model = buildChartModel(
      chart({
        series: [
          { name: 'Empty', points: [] },
          { name: 'Real', points: [[1, 1]] },
        ],
      }),
    )
    expect(model.series.map((s) => [s.key, s.name, s.color])).toEqual([['s0', 'Real', '#0a0a0a']])
  })

  it('keeps series with duplicate or missing names apart', () => {
    const model = buildChartModel(
      chart({
        series: [
          { name: 'Same', points: [[1, 1]] },
          { name: 'Same', points: [[1, 2]] },
          { points: [[1, 3]] } as unknown as { name: string; points: [number, number][] },
        ],
      }),
    )
    expect(model.rows).toEqual([{ x: 1, s0: 1, s1: 2, s2: 3 }])
    expect(model.series.map((s) => s.name)).toEqual(['Same', 'Same', 'Series 3'])
  })

  it('gives a single point a padded domain so it sits mid-plot', () => {
    const model = buildChartModel(chart({ kind: 'scatter', series: [{ name: 'A', points: [[5, 1]] }] }))
    expect(model.xDomain).toEqual([4, 6])
    expect(model.xTicks).toContain(5)
  })

  it('pads a single date by a day either side', () => {
    const at = Date.parse('2026-06-03')
    const model = buildChartModel(chart({ series: [{ name: 'A', points: [['2026-06-03', 1]] }] }))
    expect(model.xDomain).toEqual([at - 86_400_000, at + 86_400_000])
    expect(model.xTicks).toContain(at)
  })

  it('puts round ticks inside a numeric domain', () => {
    const model = buildChartModel(chart({ kind: 'scatter', series: [{ name: 'A', points: [[0, 1], [100, 2]] }] }))
    expect(model.xTicks).toEqual([0, 20, 40, 60, 80, 100])
  })

  it('pads the scatter domain so dots clear the axes, and leaves lines edge to edge', () => {
    const points: [number, number][] = [[0, 1], [100, 2]]
    expect(buildChartModel(chart({ kind: 'scatter', series: [{ name: 'A', points }] })).xDomain).toEqual([-4, 104])
    expect(buildChartModel(chart({ kind: 'line', series: [{ name: 'A', points }] })).xDomain).toEqual([0, 100])
  })

  it('centres category scatter columns with half a step either side', () => {
    const model = buildChartModel(chart({ kind: 'scatter', series: [{ name: 'A', points: [['a', 1], ['b', 2], ['c', 3]] }] }))
    expect(model.xDomain).toEqual([-0.5, 2.5])
    expect(model.xTicks).toEqual([0, 1, 2])
  })

  it('exposes per-series points for scatter plots', () => {
    const model = buildChartModel(chart({ kind: 'scatter', series: [{ name: 'A', points: [[2, 20], [1, 10], [1, 11]] }] }))
    expect(model.series[0].points).toEqual([
      { x: 2, y: 20 },
      { x: 1, y: 10 },
      { x: 1, y: 11 },
    ])
  })

  it('truncates absurd tick labels but keeps the full text for tooltips', () => {
    const long = 'category '.repeat(40).trim()
    const model = buildChartModel(chart({ kind: 'bar', series: [{ name: 'A', points: [[long, 1]] }] }))
    expect(model.formatTick(0)).toBe('category cat…')
    expect(model.formatX(0)).toBe(long)
  })

  it('falls back to a line for an unknown kind', () => {
    expect(buildChartModel(chart({ kind: 'pie' as 'line', series: [{ name: 'A', points: [[1, 1]] }] })).kind).toBe('line')
  })
})

describe('seriesColor', () => {
  it('is ink, then faint, then lighter grays that never reach white', () => {
    expect(seriesColor(0)).toBe('#0a0a0a')
    expect(seriesColor(1)).toBe('#bdbdbd')
    expect(seriesColor(2)).toBe('#d0d0d0')
    expect(seriesColor(3)).toBe('#dcdcdc')
    expect(seriesColor(40)).toBe('#dcdcdc')
  })
})

describe('formatNumber', () => {
  it('keeps small values precise, avoids grouping years, and compacts large values', () => {
    expect(formatNumber(0.5812)).toBe('0.581')
    expect(formatNumber(2019)).toBe('2019')
    expect(formatNumber(12.5)).toBe('12.5')
    expect(formatNumber(1_250_000)).toBe('1.3M')
    expect(formatNumber(45_000)).toBe('45K')
    expect(formatNumber(0)).toBe('0')
  })

  it('uses a true minus sign', () => {
    expect(formatNumber(-0.4)).toBe('−0.4')
    expect(formatNumber(-20_000)).toBe('−20K')
  })

  it('renders non-finite values as a dash', () => {
    expect(formatNumber(NaN)).toBe('—')
  })
})

describe('formatValue', () => {
  it('keeps tooltip values readable', () => {
    expect(formatValue(1234.56789)).toBe('1,234.568')
    expect(formatValue(-0.5)).toBe('−0.5')
    expect(formatValue(NaN)).toBe('—')
  })
})

describe('niceTicks', () => {
  it('steps by 1, 2 or 5 times a power of ten', () => {
    expect(niceTicks(0, 100)).toEqual([0, 20, 40, 60, 80, 100])
    expect(niceTicks(-4, 104)).toEqual([0, 20, 40, 60, 80, 100])
    expect(niceTicks(0, 7)).toEqual([0, 2, 4, 6])
  })

  it('avoids floating point noise', () => {
    expect(niceTicks(0, 1)).toEqual([0, 0.2, 0.4, 0.6, 0.8, 1])
    expect(niceTicks(4, 6)).toEqual([4, 4.5, 5, 5.5, 6])
  })

  it('copes with a flat or inverted range', () => {
    expect(niceTicks(3, 3)).toEqual([3])
    expect(niceTicks(5, 1)).toEqual([5])
  })
})

describe('dateTicks', () => {
  const day = 86_400_000

  it('lands on UTC midnights at a step that keeps the axis sparse', () => {
    const start = Date.parse('2026-06-01')
    const ticks = dateTicks(start, start + 29 * day)
    expect(ticks.length).toBeGreaterThanOrEqual(3)
    expect(ticks.length).toBeLessThanOrEqual(7)
    for (const tick of ticks) expect(tick % day).toBe(0)
  })

  it('stays sparse over many years', () => {
    const ticks = dateTicks(Date.parse('2001-01-01'), Date.parse('2026-01-01'))
    expect(ticks.length).toBeGreaterThanOrEqual(2)
    expect(ticks.length).toBeLessThanOrEqual(7)
  })

  it('falls back to the start when no midnight is in range', () => {
    const noon = Date.parse('2026-06-01T12:00:00Z')
    expect(dateTicks(noon, noon + 3_600_000)).toEqual([noon])
  })
})

describe('dual axis', () => {
  const line = (series: [string, number[]][], kind: 'line' | 'bar' | 'scatter' = 'line') =>
    buildChartModel({
      id: 'c',
      type: 'chart',
      kind,
      title: 't',
      series: series.map(([name, ys]) => ({ name, points: ys.map((y, i) => [i, y] as [number, number]) })),
    })

  it('splits two line series whose scales differ, such as degrees and dollars', () => {
    expect(line([['Temp (F)', [60, 85, 95, 70]], ['Spot ($)', [2.1, 3.4, 2.8, 3.9]]]).dualAxis).toBe(true)
  })

  it('splits series that sit in disjoint ranges even with similar spans', () => {
    expect(line([['A', [100, 110, 105]], ['B', [1, 11, 6]]]).dualAxis).toBe(true)
  })

  it('keeps series on one axis when they share a scale', () => {
    expect(line([['A', [-1.2, 0.4, 1.1]], ['B', [-0.8, 0.1, 1.4]]]).dualAxis).toBe(false)
    expect(line([['A', [10, 20, 30]], ['B', [15, 22, 41]]]).dualAxis).toBe(false)
  })

  it.each([
    ['one series', [['A', [1, 2, 3]]]],
    ['three series', [['A', [1, 2]], ['B', [100, 200]], ['C', [5, 6]]]],
    ['an empty second series', [['A', [1, 2, 3]], ['B', []]]],
    ['a single-point second series', [['A', [1, 2, 3]], ['B', [500]]]],
    ['non-finite values only', [['A', [1, 2, 3]], ['B', [NaN, Infinity]]]],
  ] as [string, [string, number[]][]][])('never splits with %s', (_, series) => {
    expect(line(series).dualAxis).toBe(false)
  })

  it('never splits bars or scatters, where one axis is the point', () => {
    const series: [string, number[]][] = [['A', [60, 85, 95]], ['B', [2, 3, 4]]]
    expect(line(series, 'bar').dualAxis).toBe(false)
    expect(line(series, 'scatter').dualAxis).toBe(false)
  })

  it('splits a flat series from a varying one on a different level', () => {
    expect(line([['A', [50, 50, 50]], ['B', [1, 2, 3]]]).dualAxis).toBe(true)
  })
})
