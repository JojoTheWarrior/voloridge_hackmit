import { act, screen, within } from '@testing-library/react'
import { createMockApi } from '../api/mock'
import { makeMission } from '../test/missions'
import { renderWithApp } from '../test/render'
import { Sidebar } from './Sidebar'

function apiWith(...missions: ReturnType<typeof makeMission>[]) {
  return createMockApi({ seed: { missions, datasets: [] } })
}

describe('Sidebar', () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }))
  afterEach(() => vi.useRealTimers())

  it('groups running missions apart from done and failed ones', async () => {
    const running = makeMission('running', { title: 'Live one' })
    const done = makeMission('done', { title: 'Finished one' })
    const failed = makeMission('failed', { title: 'Broken one' })
    renderWithApp(<Sidebar />, { api: apiWith(running, done, failed) })

    const runningGroup = await screen.findByRole('group', { name: 'Running' })
    expect(within(runningGroup).getByRole('link', { name: /Live one/ })).toBeInTheDocument()
    expect(within(runningGroup).queryByText('Finished one')).not.toBeInTheDocument()

    const doneGroup = screen.getByRole('group', { name: 'Done' })
    expect(within(doneGroup).getByRole('link', { name: /Finished one/ })).toBeInTheDocument()
    expect(within(doneGroup).getByRole('link', { name: /Broken one/ })).toBeInTheDocument()
    expect(within(doneGroup).getByRole('img', { name: 'Failed' })).toBeInTheDocument()
  })

  it('omits an empty group', async () => {
    renderWithApp(<Sidebar />, { api: apiWith(makeMission('done')) })
    await screen.findByRole('group', { name: 'Done' })
    expect(screen.queryByRole('group', { name: 'Running' })).not.toBeInTheDocument()
  })

  it('renders with no missions at all', async () => {
    renderWithApp(<Sidebar />, { api: apiWith() })
    expect(await screen.findByRole('link', { name: 'New mission' })).toBeInTheDocument()
    expect(screen.queryByRole('group')).not.toBeInTheDocument()
  })

  it('marks the mission for the current route', async () => {
    const a = makeMission('done', { title: 'Alpha' })
    const b = makeMission('done', { title: 'Beta' })
    renderWithApp(<Sidebar />, { api: apiWith(a, b), route: `/missions/${b.id}` })
    expect(await screen.findByRole('link', { name: /Beta/ })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: /Alpha/ })).not.toHaveAttribute('aria-current')
  })

  it('links to home, new mission and datasets', async () => {
    renderWithApp(<Sidebar />, { api: apiWith() })
    expect(await screen.findByRole('link', { name: 'New mission' })).toHaveAttribute('href', '/')
    expect(screen.getByRole('link', { name: 'kingdom' })).toHaveAttribute('href', '/')
    expect(screen.getByRole('link', { name: 'Datasets' })).toHaveAttribute('href', '/datasets')
  })

  it('shows a newly created mission without remounting', async () => {
    const { api } = renderWithApp(<Sidebar />, { api: apiWith() })
    await screen.findByRole('link', { name: 'New mission' })
    await act(() => api.createMission({ hypothesis: 'Fresh idea', datasetIds: [] }))
    expect(await screen.findByRole('link', { name: /Fresh idea/ })).toBeInTheDocument()
  })

  it('moves a mission to Done when it finishes', async () => {
    const running = makeMission('running', { title: 'Nearly there' })
    const api = createMockApi({ stepMs: 100, seed: { missions: [running], datasets: [] } })
    renderWithApp(<Sidebar />, { api })
    await screen.findByRole('group', { name: 'Running' })
    await act(() => vi.advanceTimersByTimeAsync(1000))
    expect(within(screen.getByRole('group', { name: 'Done' })).getByText('Nearly there')).toBeInTheDocument()
    expect(screen.queryByRole('group', { name: 'Running' })).not.toBeInTheDocument()
  })

  it('calls onNavigate when a link is followed', async () => {
    const onNavigate = vi.fn()
    renderWithApp(<Sidebar onNavigate={onNavigate} />, { api: apiWith() })
    ;(await screen.findByRole('link', { name: 'Datasets' })).click()
    expect(onNavigate).toHaveBeenCalled()
  })
})
