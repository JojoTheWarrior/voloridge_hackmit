import { render, screen, waitFor } from '@testing-library/react'
import type { ChartArtifact as ChartSpec } from '../../types'
import { ChartArtifact } from './ChartArtifact'

const chart = (over: Partial<ChartSpec>): ChartSpec => ({ id: 'c', type: 'chart', kind: 'line', title: 'Chart', series: [], ...over })

// jsdom lays nothing out, and Recharts draws nothing into a container that measures zero wide.
beforeAll(async () => {
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue(new DOMRect(0, 0, 640, 220))
  // Warm the lazy Recharts chunk: under a parallel run its first import can outlast findBy's timeout.
  await import('./ChartPlot')
}, 30_000)
afterAll(() => vi.restoreAllMocks())

/** Recharts draws a tick after mounting, so wait for the marks rather than the container. */
async function marks(selector: string, expected: number) {
  const root = await screen.findByTestId('chart-plot')
  await waitFor(() => expect(root.querySelectorAll(selector)).toHaveLength(expected))
  return [...root.querySelectorAll(selector)]
}
const plot = () => screen.findByTestId('chart-plot')

describe('ChartArtifact', () => {
  it('draws one line per series, ink first and faint second', async () => {
    render(
      <ChartArtifact
        artifact={chart({
          series: [
            { name: 'Severe share', points: [['2026-06-01', 1], ['2026-06-02', 3], ['2026-06-03', 2]] },
            { name: 'Outage hours', points: [['2026-06-01', 2], ['2026-06-02', 2], ['2026-06-03', 4]] },
          ],
        })}
      />,
    )
    const strokes = (await marks('.recharts-line-curve', 2)).map((path) => path.getAttribute('stroke'))
    // The ink series is drawn last so it sits on top.
    expect(strokes).toEqual(['#bdbdbd', '#0a0a0a'])
  })

  it('shows a legend only when there is more than one series', async () => {
    const one = { name: 'Only', points: [[1, 1], [2, 2]] as [number, number][] }
    const { unmount } = render(<ChartArtifact artifact={chart({ series: [one] })} />)
    await plot()
    expect(screen.queryByText('Only')).not.toBeInTheDocument()
    unmount()

    render(<ChartArtifact artifact={chart({ series: [one, { name: 'Other', points: [[1, 2]] }] })} />)
    await plot()
    expect(screen.getByText('Only')).toBeInTheDocument()
    expect(screen.getByText('Other')).toBeInTheDocument()
  })

  it('shows axis labels outside the plot when given', async () => {
    render(<ChartArtifact artifact={chart({ xLabel: 'Severe share', yLabel: 'Median outage hours', series: [{ name: 'A', points: [[1, 1], [2, 2]] }] })} />)
    const root = await plot()
    expect(screen.getByText('Severe share')).toBeInTheDocument()
    expect(screen.getByText('Median outage hours')).toBeInTheDocument()
    expect(root).not.toHaveTextContent('Severe share')
  })

  it('draws a dot for every valid scatter point and fades dense clouds', async () => {
    const few: [number, number][] = [[0.1, 4.2], [0.3, 9.1], [NaN, 1], [0.5, Infinity]]
    const { unmount } = render(<ChartArtifact artifact={chart({ kind: 'scatter', series: [{ name: 'Counties', points: few }] })} />)
    let dots = await marks('circle[r="3"]', 2)
    expect(dots[0]).toHaveAttribute('fill', '#0a0a0a')
    expect(dots[0]).toHaveAttribute('fill-opacity', '1')
    unmount()

    const many = Array.from({ length: 200 }, (_, index): [number, number] => [index, index % 17])
    render(<ChartArtifact artifact={chart({ kind: 'scatter', series: [{ name: 'Counties', points: many }] })} />)
    dots = await marks('circle[r="3"]', 200)
    expect(Number(dots[0].getAttribute('fill-opacity'))).toBeLessThan(1)
  })

  it('draws a bar per category', async () => {
    render(<ChartArtifact artifact={chart({ kind: 'bar', series: [{ name: 'A', points: [['West', 3], ['East', 1], ['North', 2]] }] })} />)
    const bars = await marks('.recharts-bar-rectangle path', 3)
    for (const bar of bars) expect(bar).toHaveAttribute('fill', '#0a0a0a')
  })

  it('keeps grouped bars in series order and adds a zero baseline when values go negative', async () => {
    render(
      <ChartArtifact
        artifact={chart({
          kind: 'bar',
          series: [
            { name: 'Before', points: [['a', 3], ['b', -2]] },
            { name: 'After', points: [['a', 2], ['b', -1]] },
          ],
        })}
      />,
    )
    const bars = await marks('.recharts-bar-rectangle path', 4)
    expect(bars.map((bar) => bar.getAttribute('fill'))).toEqual(['#0a0a0a', '#0a0a0a', '#bdbdbd', '#bdbdbd'])
    expect((await plot()).querySelectorAll('.recharts-reference-line-line')).toHaveLength(1)
  })

  it('draws no baseline when every bar is positive', async () => {
    render(<ChartArtifact artifact={chart({ kind: 'bar', series: [{ name: 'A', points: [['a', 3], ['b', 2]] }] })} />)
    await marks('.recharts-bar-rectangle path', 2)
    expect((await plot()).querySelectorAll('.recharts-reference-line-line')).toHaveLength(0)
  })

  it('marks a lone point with a dot so a one-point line is still visible', async () => {
    render(<ChartArtifact artifact={chart({ series: [{ name: 'A', points: [[1, 1]] }] })} />)
    await marks('.recharts-line-dot', 1)
  })

  it('truncates absurd series names in the legend with the full text on hover', async () => {
    const long = 'series '.repeat(60).trim()
    render(<ChartArtifact artifact={chart({ series: [{ name: long, points: [[1, 1]] }, { name: 'B', points: [[1, 2]] }] })} />)
    await plot()
    expect(screen.getByText(long)).toHaveClass('truncate')
    expect(screen.getByText(long)).toHaveAttribute('title', long)
  })

  it.each([
    ['no series', []],
    ['empty points', [{ name: 'A', points: [] }]],
    ['only non-finite values', [{ name: 'A', points: [[NaN, NaN], [1, Infinity]] }]],
    ['a missing series field', undefined],
  ])('shows a quiet empty state for %s', (_, series) => {
    render(<ChartArtifact artifact={chart({ series: series as ChartSpec['series'] })} />)
    expect(screen.getByText('Nothing to show')).toBeInTheDocument()
    expect(screen.queryByTestId('chart-plot')).not.toBeInTheDocument()
  })

  it('renders mixed string and number x values as categories without throwing', async () => {
    render(<ChartArtifact artifact={chart({ series: [{ name: 'A', points: [[1, 1], ['two', 2], ['2026-06-03', 3]] }] })} />)
    await marks('.recharts-line-curve', 1)
  })
})
