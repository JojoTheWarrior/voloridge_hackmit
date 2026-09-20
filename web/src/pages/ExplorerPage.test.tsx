import { act, fireEvent, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ValidationError } from '../api/index'
import { createMockApi } from '../api/mock'
import { makeExplorer, makeMission } from '../test/missions'
import { renderMissionView } from '../test/render'
import type { Mission } from '../types'
import { ExplorerPage } from './ExplorerPage'

const STEP_MS = 100

function renderExplorer(mission: Mission, id = mission.id) {
  const api = createMockApi({ stepMs: STEP_MS, seed: { missions: [mission], datasets: [] } })
  const buildExplorer = vi.spyOn(api, 'buildExplorer')
  const view = renderMissionView(<ExplorerPage />, 'explorer', { api, route: `/missions/${encodeURIComponent(id)}/explorer` })
  return { ...view, buildExplorer, user: userEvent.setup({ advanceTimers: vi.advanceTimersByTime }) }
}

const explorer = makeExplorer({ src: '/api/missions/m1/explorer/1/index.html' })
const ready = (overrides: Partial<Mission> = {}) => makeMission('done', { id: 'm1', explorer, ...overrides })
const frame = () => screen.findByTitle<HTMLIFrameElement>(explorer.title)
const changeButton = () => screen.getByRole('button', { name: 'Request a change' })

describe('ExplorerPage', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })
  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
  })

  describe('with an explorer', () => {
    it('shows it in the frame under a slim row of what it is and what you can do', async () => {
      const { container } = renderExplorer(ready({ title: 'Clinics vs floods' }))
      expect(await frame()).toHaveAttribute('src', `${explorer.src}?theme=light`)
      expect(screen.getByRole('heading', { level: 1, name: 'Clinics vs floods' })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: 'Explorer, ready' })).toHaveAttribute('aria-current', 'page')

      expect(screen.getByRole('heading', { level: 2, name: explorer.title })).toHaveClass('font-medium', 'truncate')
      expect(screen.getByText(explorer.description)).toHaveClass('text-muted', 'truncate')
      const open = screen.getByRole('link', { name: 'Open in new tab' })
      expect(open).toHaveAttribute('href', `${explorer.src}?theme=light`)
      expect(open).toHaveAttribute('target', '_blank')
      expect(open).toHaveAttribute('rel', 'noreferrer')
      expect(changeButton()).not.toHaveAttribute('aria-disabled', 'true')
      expect(screen.queryByRole('button', { name: /rebuild/i })).not.toBeInTheDocument()
      expect(container.querySelector('[class*="bg-ink"]')).toBeNull()
    })

    it('gives the frame all the height under the row', async () => {
      renderExplorer(ready())
      const wrapper = (await frame()).parentElement!
      expect(wrapper).toHaveClass('min-h-0', 'flex-1')
      expect(wrapper.parentElement).toHaveClass('flex', 'h-full', 'flex-col')
    })

    it('sends a change request to Devin, keeps the current build up meanwhile, then swaps in the new one', async () => {
      const { buildExplorer, user } = renderExplorer(ready())
      const before = await frame()
      await user.click(changeButton())
      await user.type(screen.getByRole('textbox', { name: 'What should change?' }), 'Add a heatmap layer')
      await user.click(screen.getByRole('button', { name: 'Send to Devin' }))
      expect(buildExplorer).toHaveBeenCalledExactlyOnceWith('m1', 'Add a heatmap layer')

      expect(await screen.findByText('Devin is updating this')).toBeInTheDocument()
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
      expect(await frame()).toBe(before)
      expect(screen.getByRole('link', { name: 'Explorer, in progress' })).toBeInTheDocument()

      await act(() => vi.advanceTimersByTimeAsync(STEP_MS))
      expect(screen.queryByText('Devin is updating this')).not.toBeInTheDocument()
      const rebuilt = document.querySelector('iframe')
      expect(rebuilt).not.toBe(before)
      expect(rebuilt).toHaveAttribute('src', '/api/missions/m1/explorer/2/index.html?theme=light')
      expect(screen.getByText(/Add a heatmap layer$/)).toBeInTheDocument()
      expect(changeButton()).not.toHaveAttribute('aria-disabled', 'true')
    })

    it('rebuilds when the change request is left empty', async () => {
      const { buildExplorer, user } = renderExplorer(ready())
      await frame()
      await user.click(changeButton())
      await user.click(screen.getByRole('button', { name: 'Send to Devin' }))
      expect(buildExplorer).toHaveBeenCalledExactlyOnceWith('m1', '')
    })

    it('shows the server\'s objection in the dialog', async () => {
      const { buildExplorer, user } = renderExplorer(ready())
      buildExplorer.mockRejectedValueOnce(new ValidationError('text', 'Keep instructions under 2,000 characters'))
      await frame()
      await user.click(changeButton())
      await user.click(screen.getByRole('button', { name: 'Send to Devin' }))
      expect(await within(screen.getByRole('dialog')).findByText('Keep instructions under 2,000 characters')).toBeInTheDocument()
      expect(screen.queryByText('Devin is updating this')).not.toBeInTheDocument()
    })

    it('opens the change dialog from the slow-loading note too', async () => {
      const { user } = renderExplorer(ready())
      await frame()
      await act(() => vi.advanceTimersByTimeAsync(20_001))
      await user.click(screen.getByRole('button', { name: 'request a change' }))
      expect(screen.getByRole('dialog', { name: 'Request a change' })).toBeInTheDocument()
    })

    describe('while Devin is updating it', () => {
      it('keeps the current build on screen with a quiet note, and the change button at rest', async () => {
        const { buildExplorer, user } = renderExplorer(ready({ status: 'working', explorerPending: true }))
        expect(await frame()).toHaveAttribute('src', `${explorer.src}?theme=light`)
        const note = screen.getByText('Devin is updating this')
        expect(note.closest('[role="status"]')?.querySelector('svg')).toHaveClass('animate-spin')
        expect(changeButton()).toHaveAttribute('aria-disabled', 'true')
        expect(changeButton()).toHaveClass('text-muted', 'cursor-default')

        await user.click(changeButton())
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
        expect(buildExplorer).not.toHaveBeenCalled()
        expect(screen.getByRole('link', { name: 'Open in new tab' })).toBeInTheDocument()
      })
    })
  })

  describe('while the first build is on its way', () => {
    it('fills the area with a calm building state', async () => {
      renderExplorer(makeMission('working', { explorerPending: true }))
      const state = (await screen.findByRole('heading', { name: 'Devin is building the explorer' })).closest('[role="status"]')!
      expect(state).toHaveTextContent('Devin is building the explorer')
      expect(screen.getByText('This can take several minutes. You can keep using the thread meanwhile.')).toHaveClass('text-muted')
      expect(document.querySelector('iframe')).toBeNull()
      expect(screen.queryByRole('button', { name: 'Build explorer' })).not.toBeInTheDocument()
    })
  })

  describe('with no explorer', () => {
    const build = () => screen.findByRole('button', { name: 'Build explorer' })
    const wish = () => screen.getByRole('textbox', { name: 'Anything specific it should show?' })

    it('invites you to have one built, and says not every mission needs one', async () => {
      const { container } = renderExplorer(makeMission('waiting'))
      expect(await screen.findByRole('heading', { level: 2, name: 'Explore the findings' })).toBeInTheDocument()
      expect(screen.getByText(/places or items rather than statistics/)).toHaveClass('text-muted')
      expect(screen.getByText(/Not every mission needs one/)).toHaveClass('text-muted')
      expect(await build()).toHaveClass('border', 'border-line')
      expect(container.querySelector('[class*="bg-ink"]')).toBeNull()
      expect(screen.queryByText(/worth waiting/)).not.toBeInTheDocument()
    })

    it('builds with no instructions, then waits, then shows the explorer', async () => {
      const mission = makeMission('waiting')
      const { buildExplorer, user } = renderExplorer(mission)
      await user.dblClick(await build())
      expect(buildExplorer).toHaveBeenCalledExactlyOnceWith(mission.id, '')
      expect(await screen.findByRole('status')).toHaveTextContent('Devin is building the explorer')

      await act(() => vi.advanceTimersByTimeAsync(STEP_MS))
      expect(await screen.findByTitle(mission.title)).toHaveAttribute('src', `/api/missions/${mission.id}/explorer/1/index.html?theme=light`)
    })

    it('passes along what it should show, on Enter too', async () => {
      const mission = makeMission('waiting')
      const { buildExplorer, user } = renderExplorer(mission)
      await build()
      await user.type(wish(), 'A map of the clinics{Enter}')
      expect(buildExplorer).toHaveBeenCalledExactlyOnceWith(mission.id, 'A map of the clinics')
    })

    it('rests the button while the request itself is in flight, keeping what you typed', async () => {
      const { buildExplorer, user } = renderExplorer(makeMission('waiting'))
      let finish = () => {}
      buildExplorer.mockImplementationOnce(() => new Promise<void>((resolve) => (finish = resolve)))
      await build()
      await user.type(wish(), 'A map{Enter}')
      const resting = await build()
      expect(resting).toHaveAttribute('aria-disabled', 'true')
      expect(resting).toHaveClass('text-muted', 'cursor-default')
      await user.click(resting)
      expect(buildExplorer).toHaveBeenCalledTimes(1)
      expect(wish()).toHaveValue('A map')
      await act(async () => finish())
    })

    it('comes back with what you typed and a quiet note when the request fails', async () => {
      const { buildExplorer, user } = renderExplorer(makeMission('waiting'))
      buildExplorer.mockRejectedValueOnce(new TypeError('Failed to fetch'))
      await build()
      await user.type(wish(), 'A map{Enter}')
      expect(await screen.findByText('That did not send. Try again.')).toBeInTheDocument()
      expect(wish()).toHaveValue('A map')
      await user.click(await build())
      expect(buildExplorer).toHaveBeenCalledTimes(2)
    })

    it('shows the server\'s objection under the input', async () => {
      const { buildExplorer, user } = renderExplorer(makeMission('waiting'))
      buildExplorer.mockRejectedValueOnce(new ValidationError('text', 'Keep instructions under 2,000 characters'))
      await build()
      fireEvent.change(wish(), { target: { value: 'x'.repeat(2001) } })
      await user.click(await build())
      expect(await screen.findByText('Keep instructions under 2,000 characters')).toBeInTheDocument()
    })

    it('suggests waiting for a conclusion when there is none, but still lets you build', async () => {
      const mission = makeMission('working')
      const { buildExplorer, user } = renderExplorer(mission)
      expect(await screen.findByText(/usually worth waiting/)).toHaveClass('text-muted')
      await user.click(await build())
      expect(buildExplorer).toHaveBeenCalledExactlyOnceWith(mission.id, '')
    })
  })

  it('shows not found for an unknown mission', async () => {
    renderExplorer(ready(), 'nope')
    expect(await screen.findByRole('heading', { name: 'Mission not found' })).toBeInTheDocument()
    expect(document.querySelector('iframe')).toBeNull()
  })
})
