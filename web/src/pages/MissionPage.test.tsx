import { act, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { buildResult } from '../api/fixtures'
import { createMockApi, SEED_SLOWDOWN } from '../api/mock'
import { makeMission } from '../test/missions'
import { renderWithApp } from '../test/render'
import type { Mission } from '../types'
import { MissionPage } from './MissionPage'

const STEP_MS = 100

function renderMission(missions: Mission[], id: string) {
  const api = createMockApi({ stepMs: STEP_MS, seed: { missions, datasets: [] } })
  return renderWithApp(
    <Routes>
      <Route path="missions/:id" element={<MissionPage />} />
      <Route path="/" element={<p>home page</p>} />
    </Routes>,
    { api, route: `/missions/${id}` },
  )
}

describe('MissionPage', () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }))
  afterEach(() => vi.useRealTimers())

  it('shows a running mission with its steps expanded and no result', async () => {
    const mission = makeMission('running', { hypothesis: 'Does A lead B?' })
    renderMission([mission], mission.id)

    expect(await screen.findByText('Does A lead B?')).toBeInTheDocument()
    const steps = within(screen.getByRole('list', { name: 'Progress' })).getAllByRole('listitem')
    expect(steps.map((s) => s.textContent)).toEqual(['Planned the test', 'Pulled the data', 'Running the permutation test'])
    expect(steps[2]).toHaveAttribute('aria-current', 'step')
    expect(screen.queryByRole('button', { name: /Worked for/ })).not.toBeInTheDocument()
    expect(screen.queryByText('Correlation')).not.toBeInTheDocument()
  })

  it('collapses the steps of a done mission and expands them on click', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    const mission = makeMission('done', { elapsedSeconds: 252, result: buildResult('x', { strength: 0.6 }) })
    renderMission([mission], mission.id)

    const toggle = await screen.findByRole('button', { name: 'Worked for 4m 12s' })
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('list', { name: 'Progress' })).not.toBeInTheDocument()

    await user.click(toggle)
    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    expect(within(screen.getByRole('list', { name: 'Progress' })).getAllByRole('listitem')).toHaveLength(5)

    await user.click(toggle)
    expect(screen.queryByRole('list', { name: 'Progress' })).not.toBeInTheDocument()
  })

  it('shows the result of a done mission', async () => {
    const result = {
      ...buildResult('x'),
      seriesA: 'Wind speed',
      seriesB: 'PM2.5',
      correlation: -0.41,
      bestLagDays: 1,
      pValue: 0.0004,
      n: 120,
      note: 'First paragraph.\n\nSecond paragraph.',
      verdict: 'A real but modest link.',
    }
    const mission = makeMission('done', { result })
    renderMission([mission], mission.id)

    const card = await screen.findByRole('region', { name: 'Result' })
    expect(within(card).getByText('Wind speed')).toBeInTheDocument()
    expect(within(card).getByText('PM2.5')).toBeInTheDocument()
    expect(within(card).getByText('−0.41')).toBeInTheDocument()
    expect(within(card).getByText('1 day')).toBeInTheDocument()
    expect(within(card).getByText('<0.001')).toBeInTheDocument()
    expect(within(card).getByText('120 days')).toBeInTheDocument()
    expect(within(card).getByText('First paragraph.').tagName).toBe('P')
    expect(within(card).getByText('Second paragraph.').tagName).toBe('P')
    expect(within(card).getByText('A real but modest link.')).toBeInTheDocument()
  })

  it.each([
    [0, 'Same day'],
    [3, '3 days'],
  ])('describes a best lag of %i as %s', async (bestLagDays, text) => {
    const mission = makeMission('done', { result: { ...buildResult('x'), bestLagDays } })
    renderMission([mission], mission.id)
    expect(await screen.findByText(text)).toBeInTheDocument()
  })

  it('shows the error of a failed mission instead of a result', async () => {
    const mission = makeMission('failed', { error: 'No series found.' })
    renderMission([mission], mission.id)

    expect(await screen.findByRole('alert')).toHaveTextContent('This mission failed')
    expect(screen.getByRole('alert')).toHaveTextContent('No series found.')
    expect(screen.queryByRole('region', { name: 'Result' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Worked for/ })).toBeInTheDocument()
  })

  it('shows not found for an unknown id, with a way home', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    renderMission([], 'nope')
    expect(await screen.findByRole('heading', { name: 'Mission not found' })).toBeInTheDocument()
    await user.click(screen.getByRole('link', { name: 'Start a new mission' }))
    expect(screen.getByText('home page')).toBeInTheDocument()
  })

  it('updates live from running to done', async () => {
    const mission = makeMission('running')
    renderMission([mission], mission.id)
    await screen.findByRole('list', { name: 'Progress' })

    await act(() => vi.advanceTimersByTimeAsync(STEP_MS * SEED_SLOWDOWN))
    expect(screen.getByText('Drawing the chart')).toHaveAttribute('aria-current', 'step')

    await act(() => vi.advanceTimersByTimeAsync(STEP_MS * SEED_SLOWDOWN * 2))
    expect(await screen.findByRole('region', { name: 'Result' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Worked for/ })).toHaveAttribute('aria-expanded', 'false')
  })
})
