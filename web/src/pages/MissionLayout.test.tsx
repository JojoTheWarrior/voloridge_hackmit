import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App } from '../App'
import type { Api } from '../api/index'
import { createMockApi } from '../api/mock'
import { makeExplorer, makeMission, makeReport } from '../test/missions'
import { renderWithApp } from '../test/render'
import type { Mission } from '../types'

function renderApp(missions: Mission[], route: string, wrap: (api: Api) => Api = (api) => api) {
  return renderWithApp(<App />, { api: wrap(createMockApi({ seed: { missions, datasets: [] } })), route })
}

const tabs = () => within(screen.getByRole('navigation', { name: 'Mission views' }))
const current = () => tabs().getAllByRole('link').filter((link) => link.getAttribute('aria-current') === 'page').map((link) => link.textContent)

describe('MissionLayout', () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }))
  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
  })

  it('moves between the thread, the report and the explorer under one header', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    const mission = makeMission('done', { id: 'm1', title: 'Clinics vs floods', report: makeReport(), explorer: makeExplorer() })
    renderApp([mission], '/missions/m1')
    const title = await screen.findByRole('heading', { level: 1, name: 'Clinics vs floods' })
    expect(screen.getByRole('log', { name: 'Mission thread' })).toBeInTheDocument()
    expect(current()).toEqual(['Thread'])

    await user.click(tabs().getByRole('link', { name: /^Report/ }))
    expect(await screen.findByRole('heading', { level: 2, name: 'Wind leads dust by two days' })).toBeInTheDocument()
    expect(screen.queryByRole('log')).not.toBeInTheDocument()
    expect(current()).toEqual(['Report, ready'])

    await user.click(tabs().getByRole('link', { name: /^Explorer/ }))
    expect(await screen.findByTitle('Clinics by flood risk')).toBeInTheDocument()
    expect(current()).toEqual(['Explorer, ready'])

    await user.click(tabs().getByRole('link', { name: 'Thread' }))
    expect(await screen.findByRole('log', { name: 'Mission thread' })).toBeInTheDocument()
    expect(screen.getAllByRole('heading', { level: 1 })).toEqual([title])
  })

  it.each(['/missions/m1/report', '/missions/m1/explorer'])('opens %s directly', async (route) => {
    renderApp([makeMission('waiting', { id: 'm1' })], route)
    expect(await screen.findByRole('navigation', { name: 'Mission views' })).toBeInTheDocument()
    expect(current()).toHaveLength(1)
    expect(screen.queryByRole('log')).not.toBeInTheDocument()
  })

  it('prefills a report follow-up in the thread and sends only after confirmation', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    const { api } = renderApp([makeMission('done', { id: 'm1', report: makeReport() })], '/missions/m1/report')
    const send = vi.spyOn(api, 'sendMessage')
    await user.click(await screen.findByRole('link', { name: 'Does it hold over two years?' }))
    const reply = await screen.findByRole('textbox', { name: 'Reply to Devin' })
    expect(reply).toHaveValue('Does it hold over two years?')
    expect(reply).toHaveFocus()
    expect(send).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Send reply' }))
    expect(send).toHaveBeenCalledExactlyOnceWith('m1', 'Does it hold over two years?')
  })

  it('reaches the report and the explorer from their cards in the thread', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    const events = [...makeMission('done').events, { id: 'report', at: '2026-09-20T12:30:00Z', kind: 'report' as const }, { id: 'explorer', at: '2026-09-20T12:40:00Z', kind: 'explorer' as const }]
    renderApp([makeMission('done', { id: 'm1', events, report: makeReport(), explorer: makeExplorer() })], '/missions/m1')
    await user.click(await screen.findByRole('link', { name: 'Open explorer' }))
    expect(current()).toEqual(['Explorer, ready'])
    await user.click(tabs().getByRole('link', { name: 'Thread' }))
    await user.click(await screen.findByRole('link', { name: 'View report' }))
    expect(current()).toEqual(['Report, ready'])
  })

  it.each(['', '/report', '/explorer'])('shows not found at "/missions/nope%s"', async (suffix) => {
    renderApp([makeMission('done')], `/missions/nope${suffix}`)
    expect(await screen.findByRole('heading', { level: 1, name: 'Mission not found' })).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Mission views' })).not.toBeInTheDocument()
  })

  it.each(['', '/report', '/explorer'])('shows loading at "/missions/m1%s" while the mission is loading', async (suffix) => {
    renderApp([makeMission('done', { id: 'm1' })], `/missions/m1${suffix}`, (api) => ({ ...api, getMission: () => new Promise(() => {}) }))
    await screen.findByRole('navigation', { name: 'Main' })
    expect(within(screen.getByRole('main')).getByRole('status')).toHaveTextContent('Loading mission')
  })

  it('explains an initial connection failure instead of showing a blank page', async () => {
    renderApp([], '/missions/m1', (api) => ({ ...api, getMission: async () => { throw new Error('offline') } }))
    expect(await screen.findByRole('heading', { name: 'Reconnecting to Kingdom' })).toBeInTheDocument()
    expect(screen.queryByText('Mission not found')).not.toBeInTheDocument()
  })
})
