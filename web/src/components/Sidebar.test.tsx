import { act, screen, within } from '@testing-library/react'
import { createMockApi } from '../api/mock'
import { SCRIPT } from '../api/script'
import { makeMission } from '../test/missions'
import { renderWithApp } from '../test/render'
import { Sidebar } from './Sidebar'

function apiWith(...missions: ReturnType<typeof makeMission>[]) {
  return createMockApi({ seed: { missions, datasets: [] } })
}

describe('Sidebar', () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }))
  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
  })

  it('groups working, waiting and failed missions as active, apart from done ones', async () => {
    const working = makeMission('working', { title: 'Live one' })
    const waiting = makeMission('waiting', { title: 'Asking one' })
    const failed = makeMission('failed', { title: 'Broken one' })
    const done = makeMission('done', { title: 'Finished one' })
    renderWithApp(<Sidebar />, { api: apiWith(working, waiting, failed, done) })

    const active = await screen.findByRole('group', { name: 'Active' })
    expect(within(active).getAllByRole('link').map((l) => l.textContent)).toEqual(['Broken one', 'Asking one', 'Live one'])
    expect(within(active).getByRole('img', { name: 'Working' })).toBeInTheDocument()
    expect(within(active).getByRole('img', { name: 'Waiting for you' })).toBeInTheDocument()
    expect(within(active).getByRole('img', { name: 'Failed' })).toBeInTheDocument()

    const doneGroup = screen.getByRole('group', { name: 'Done' })
    expect(within(doneGroup).getAllByRole('link').map((l) => l.textContent)).toEqual(['Finished one'])
    expect(within(doneGroup).getByRole('img', { name: 'Done' })).toBeInTheDocument()
  })

  it('greys out done missions only', async () => {
    const waiting = makeMission('waiting', { title: 'Asking one' })
    const done = makeMission('done', { title: 'Finished one' })
    renderWithApp(<Sidebar />, { api: apiWith(waiting, done) })
    expect(await screen.findByRole('link', { name: /Finished one/ })).toHaveClass('text-muted')
    expect(screen.getByRole('link', { name: /Asking one/ })).toHaveClass('text-ink')
  })

  it('omits an empty group', async () => {
    renderWithApp(<Sidebar />, { api: apiWith(makeMission('done')) })
    await screen.findByRole('group', { name: 'Done' })
    expect(screen.queryByRole('group', { name: 'Active' })).not.toBeInTheDocument()
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

  it('keeps a mission active while it waits, and moves it to Done once marked done', async () => {
    const working = makeMission('working', { title: 'Nearly there' })
    const api = createMockApi({ stepMs: 100, seed: { missions: [working], datasets: [] } })
    renderWithApp(<Sidebar />, { api })
    expect(await screen.findByRole('img', { name: 'Working' })).toBeInTheDocument()

    await act(() => vi.advanceTimersByTimeAsync(100 * SCRIPT.length))
    expect(within(screen.getByRole('group', { name: 'Active' })).getByRole('img', { name: 'Waiting for you' })).toBeInTheDocument()

    await act(() => api.markDone(working.id))
    expect(within(await screen.findByRole('group', { name: 'Done' })).getByRole('link', { name: /Nearly there/ })).toHaveClass('text-muted')
    expect(screen.queryByRole('group', { name: 'Active' })).not.toBeInTheDocument()
  })

  it('moves a done mission back to Active when a reply reopens it', async () => {
    const done = makeMission('done', { title: 'Back again' })
    const api = apiWith(done)
    renderWithApp(<Sidebar />, { api })
    await screen.findByRole('group', { name: 'Done' })
    await act(() => api.sendMessage(done.id, 'One more thing'))
    expect(within(await screen.findByRole('group', { name: 'Active' })).getByText('Back again')).toBeInTheDocument()
    expect(screen.queryByRole('group', { name: 'Done' })).not.toBeInTheDocument()
  })

  it('notes demo mode in the footer', async () => {
    renderWithApp(<Sidebar />, { api: createMockApi({ demo: true, seed: { missions: [], datasets: [] } }) })
    expect(await screen.findByText('Demo mode')).toBeInTheDocument()
  })

  it('says nothing about demo mode against real Devin', async () => {
    const api = apiWith()
    const getMeta = vi.spyOn(api, 'getMeta')
    renderWithApp(<Sidebar />, { api })
    await screen.findByRole('link', { name: 'New mission' })
    await act(async () => void (await getMeta.mock.results[0].value))
    expect(screen.queryByText('Demo mode')).not.toBeInTheDocument()
  })

  it('calls onNavigate when a link is followed', async () => {
    const onNavigate = vi.fn()
    renderWithApp(<Sidebar onNavigate={onNavigate} />, { api: apiWith() })
    const link = await screen.findByRole('link', { name: 'Datasets' })
    await act(async () => link.click())
    expect(onNavigate).toHaveBeenCalled()
  })
})
