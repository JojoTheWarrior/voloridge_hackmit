import { act, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Link, Route, Routes } from 'react-router-dom'
import type { Api } from '../api/index'
import { createMockApi } from '../api/mock'
import { REPLY_TEXT, SCRIPT } from '../api/script'
import { makeMission } from '../test/missions'
import { renderMissionView, renderWithApp } from '../test/render'
import type { Artifact, Mission } from '../types'
import { MissionLayout } from './MissionLayout'
import { MissionPage } from './MissionPage'

vi.mock('../components/artifacts/ArtifactView', () => ({
  ArtifactView: ({ artifact }: { artifact: Artifact }) => <div data-testid="artifact">{artifact.title}</div>,
}))

const STEP_MS = 100
const FIRST_STEP = 'Read the linked datasets'

function renderMission(missions: Mission[], id: string, wrap: (api: Api) => Api = (api) => api) {
  const api = wrap(createMockApi({ stepMs: STEP_MS, seed: { missions, datasets: [] } }))
  return renderMissionView(<MissionPage />, '', { api, route: `/missions/${id}` })
}

const replyBox = () => screen.getByRole('textbox', { name: 'Reply to Devin' })

describe('MissionPage', () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }))
  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
  })

  it('shows a working mission as a live thread with no conclusion yet', async () => {
    const mission = makeMission('working', { title: 'A vs B', hypothesis: 'Does A lead B?' })
    renderMission([mission], mission.id)

    expect(await screen.findByText('Does A lead B?')).toHaveClass('bg-fill')
    expect(screen.getByRole('heading', { name: 'A vs B' })).toBeInTheDocument()
    expect(screen.getByText('Devin is working')).toBeInTheDocument()
    expect(screen.getByText(FIRST_STEP)).not.toHaveAttribute('aria-current')
    expect(screen.getByText('Test the relationship at each lag')).toHaveAttribute('aria-current', 'step')
    expect(screen.queryByRole('region', { name: 'Conclusion' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Show the work' })).not.toBeInTheDocument()
    expect(replyBox()).toBeInTheDocument()
  })

  it('updates live from working to waiting, with the artifact and the conclusion', async () => {
    const mission = makeMission('working')
    renderMission([mission], mission.id)
    await screen.findByText('Devin is working')

    await act(() => vi.advanceTimersByTimeAsync(STEP_MS * SCRIPT.length))
    expect(screen.getByText('Waiting for you')).toBeInTheDocument()
    expect(screen.getAllByTestId('artifact')).toHaveLength(3)
    expect(screen.getByRole('region', { name: 'Conclusion' })).toBeInTheDocument()
    expect(screen.getByText(FIRST_STEP)).toBeVisible()
  })

  it('shows what Devin is asking above the reply box', async () => {
    const mission = makeMission('waiting', { needsUser: 'Should I drop the outlier county?' })
    renderMission([mission], mission.id)
    const question = await screen.findByText('Should I drop the outlier county?')
    expect(question.compareDocumentPosition(replyBox()) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('has no callout when Devin is not asking anything', async () => {
    const mission = makeMission('waiting')
    renderMission([mission], mission.id)
    await screen.findByText('Waiting for you')
    expect(screen.queryByText('Devin asks')).not.toBeInTheDocument()
  })

  it('sends a reply into the thread, then shows the answer', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    const mission = makeMission('waiting', { needsUser: 'Should I drop the outlier county?' })
    const { api } = renderMission([mission], mission.id)
    const sendMessage = vi.spyOn(api, 'sendMessage')
    await screen.findByText('Waiting for you')

    await user.type(replyBox(), 'Yes, drop it{Enter}')
    expect(sendMessage).toHaveBeenCalledExactlyOnceWith(mission.id, 'Yes, drop it')
    expect(await screen.findByText('Yes, drop it')).toHaveClass('bg-fill')
    expect(replyBox()).toHaveValue('')
    expect(screen.getByText('Devin is working')).toBeInTheDocument()
    expect(screen.queryByText('Should I drop the outlier county?')).not.toBeInTheDocument()

    await act(() => vi.advanceTimersByTimeAsync(STEP_MS))
    expect(screen.getByText(REPLY_TEXT)).toBeInTheDocument()
    expect(screen.getByText('Waiting for you')).toBeInTheDocument()
  })

  it('marks a mission done, folding the work behind one line', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    const mission = makeMission('waiting', { hypothesis: 'Does A lead B?' })
    renderMission([mission], mission.id)

    await user.click(await screen.findByRole('button', { name: 'Mark done' }))
    const toggle = await screen.findByRole('button', { name: 'Show the work' })
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByText('Done')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Mark done' })).not.toBeInTheDocument()
    expect(screen.getByText('Does A lead B?')).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Conclusion' })).toBeInTheDocument()
    expect(screen.queryByText(FIRST_STEP)).not.toBeInTheDocument()
    expect(screen.queryByTestId('artifact')).not.toBeInTheDocument()

    await user.click(toggle)
    expect(screen.getByText(FIRST_STEP)).toBeInTheDocument()
    expect(screen.getAllByTestId('artifact')).toHaveLength(3)
    expect(screen.getAllByText('Does A lead B?')).toHaveLength(1)
  })

  it('reopens a done mission when you reply to it', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    const mission = makeMission('done')
    renderMission([mission], mission.id)
    await screen.findByRole('button', { name: 'Show the work' })

    await user.type(replyBox(), 'One more thing{Enter}')
    expect(await screen.findByText('Devin is working')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Mark done' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Show the work' })).not.toBeInTheDocument()
    expect(screen.getByText(FIRST_STEP)).toBeInTheDocument()
  })

  it('shows every event of a done mission that never reached a conclusion', async () => {
    const mission = makeMission('done', { events: makeMission('working').events })
    renderMission([mission], mission.id)
    expect(await screen.findByText(FIRST_STEP)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Show the work' })).not.toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Conclusion' })).not.toBeInTheDocument()
  })

  it('stops the spinner on a step left active by a mission that is no longer working', async () => {
    const mission = makeMission('failed')
    renderMission([mission], mission.id)
    expect(await screen.findByText(FIRST_STEP)).not.toHaveAttribute('aria-current')
  })

  it('shows the error of a failed mission, which can still be marked done', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    const mission = makeMission('failed')
    renderMission([mission], mission.id)

    expect(await screen.findByRole('alert')).toHaveTextContent('It broke.')
    expect(screen.getByText('Failed')).toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Conclusion' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Mark done' }))
    expect(await screen.findByText('Done')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toBeInTheDocument()
  })

  it('links to the Devin session when there is one', async () => {
    const mission = makeMission('working', { sessionUrl: 'https://app.devin.ai/sessions/devin-abc' })
    renderMission([mission], mission.id)
    expect(await screen.findByRole('link', { name: 'Open in Devin' })).toHaveAttribute('href', 'https://app.devin.ai/sessions/devin-abc')
  })

  it('shows not found for an unknown id, with a way home', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    renderMission([], 'nope')
    expect(await screen.findByRole('heading', { name: 'Mission not found' })).toBeInTheDocument()
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
    await user.click(screen.getByRole('link', { name: 'Start a new mission' }))
    expect(screen.getByText('home page')).toBeInTheDocument()
  })

  it('keeps the thread and says it is reconnecting when the server drops away', async () => {
    const mission = makeMission('working', { hypothesis: 'Does A lead B?' })
    let down = false
    renderMission([mission], mission.id, (api) => ({
      ...api,
      getMission: (id) => (down ? Promise.reject(new TypeError('Failed to fetch')) : api.getMission(id)),
    }))
    await screen.findByText('Devin is working')

    down = true
    await act(() => vi.advanceTimersByTimeAsync(STEP_MS))
    expect(screen.getByText('Reconnecting')).toBeInTheDocument()
    expect(screen.getByText('Does A lead B?')).toBeInTheDocument()

    down = false
    await act(() => vi.advanceTimersByTimeAsync(STEP_MS))
    expect(screen.queryByText('Reconnecting')).not.toBeInTheDocument()
  })

  describe('auto-scroll', () => {
    /** jsdom lays nothing out, so the thread's scroll geometry is faked. */
    function fakeScroll(log: HTMLElement, geometry: { scrollHeight: number; clientHeight: number; scrollTop: number }) {
      const state = { ...geometry }
      for (const key of Object.keys(state) as (keyof typeof state)[]) {
        Object.defineProperty(log, key, { configurable: true, get: () => state[key], set: (value) => (state[key] = value) })
      }
      return state
    }

    async function renderScrolled(distanceFromBottom: number) {
      const mission = makeMission('working')
      renderMission([mission], mission.id)
      const log = await screen.findByRole('log', { name: 'Mission thread' })
      const state = fakeScroll(log, { scrollHeight: 2000, clientHeight: 500, scrollTop: 1500 - distanceFromBottom })
      act(() => void log.dispatchEvent(new Event('scroll')))
      state.scrollHeight = 2400
      await act(() => vi.advanceTimersByTimeAsync(STEP_MS))
      return state
    }

    it.each([0, 80])('follows new events when the reader is %ipx from the bottom', async (distance) => {
      expect((await renderScrolled(distance)).scrollTop).toBe(2400)
    })

    it.each([81, 1500])('leaves the reader alone when they are %ipx up the thread', async (distance) => {
      expect((await renderScrolled(distance)).scrollTop).toBe(1500 - distance)
    })

    it('jumps to your own reply even from further up', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const mission = makeMission('waiting')
      renderMission([mission], mission.id)
      const log = await screen.findByRole('log', { name: 'Mission thread' })
      const state = fakeScroll(log, { scrollHeight: 2000, clientHeight: 500, scrollTop: 0 })
      act(() => void log.dispatchEvent(new Event('scroll')))

      await user.type(replyBox(), 'Look here{Enter}')
      await screen.findByText('Look here')
      expect(state.scrollTop).toBe(2000)
    })
  })

  it('starts each mission afresh when moving between them', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    const first = makeMission('done', { title: 'First' })
    const second = makeMission('done', { title: 'Second' })
    const api = createMockApi({ stepMs: STEP_MS, seed: { missions: [first, second], datasets: [] } })
    renderWithApp(
      <Routes>
        <Route path="missions/:id" element={<><Link to={`/missions/${second.id}`}>next</Link><MissionLayout /></>}>
          <Route index element={<MissionPage />} />
        </Route>
      </Routes>,
      { api, route: `/missions/${first.id}` },
    )
    await user.click(await screen.findByRole('button', { name: 'Show the work' }))
    await user.type(replyBox(), 'half a thought')

    await user.click(screen.getByRole('link', { name: 'next' }))
    expect(await screen.findByRole('heading', { name: 'Second' })).toBeInTheDocument()
    expect(within(screen.getByRole('log')).queryByText(FIRST_STEP)).not.toBeInTheDocument()
    expect(replyBox()).toHaveValue('')
  })
})
