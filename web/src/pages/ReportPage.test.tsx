import { act, fireEvent, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMockApi } from '../api/mock'
import { makeMission, makeReport } from '../test/missions'
import { renderMissionView } from '../test/render'
import type { Artifact, Mission } from '../types'
import { ReportPage } from './ReportPage'

vi.mock('../components/artifacts/ArtifactView', () => ({
  ArtifactView: ({ artifact }: { artifact: Artifact }) => <div data-testid="artifact">{artifact.id}</div>,
}))

const STEP_MS = 100

function renderReport(mission: Mission, id = mission.id) {
  const api = createMockApi({ stepMs: STEP_MS, seed: { missions: [mission], datasets: [] } })
  const generateReport = vi.spyOn(api, 'generateReport')
  const view = renderMissionView(<ReportPage />, 'report', { api, route: `/missions/${encodeURIComponent(id)}/report` })
  return { ...view, generateReport, user: userEvent.setup({ advanceTimers: vi.advanceTimersByTime }) }
}

const headline = () => screen.findByRole('heading', { level: 2, name: 'Wind leads dust by two days' })

describe('ReportPage', () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }))
  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
  })

  describe('with a report', () => {
    it('sets the finding as a short paper under the mission header', async () => {
      renderReport(makeMission('done', { title: 'Wind vs dust', report: makeReport({ generatedAt: '2026-09-20T12:30:00' }) }))
      expect(await headline()).toBeInTheDocument()
      expect(screen.getByRole('heading', { level: 1, name: 'Wind vs dust' })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: 'Report, ready' })).toHaveAttribute('aria-current', 'page')
      expect(screen.getByText(/^Mission report/)).toHaveClass('text-muted')
      expect(screen.getByText('20 Sep 2026')).toHaveClass('font-mono')
      expect(screen.getByText(/^When the wind picks up/).tagName).toBe('P')
      expect(screen.getByText('0.58')).toHaveClass('font-mono')
      expect(screen.getByText('Best lag').tagName).toBe('DT')
    })

    it('features the named artifacts from the thread, in the report\'s order, skipping ids it cannot find', async () => {
      renderReport(makeMission('done', { report: makeReport({ keyArtifactIds: ['a2', 'gone', 'a1'] }) }))
      await headline()
      expect(screen.getAllByTestId('artifact').map((node) => node.textContent)).toEqual(['a2', 'a1'])
    })

    it('numbers the steps, label in ink and takeaway muted', async () => {
      renderReport(makeMission('done', { report: makeReport() }))
      await headline()
      const steps = within(screen.getByRole('region', { name: 'How we got there' })).getAllByRole('listitem')
      expect(steps).toHaveLength(2)
      expect(within(steps[1]).getByText('2')).toHaveClass('font-mono')
      expect(within(steps[1]).getByText('Test each lag')).toHaveClass('font-medium')
      expect(within(steps[1]).getByText('Two days stands out.')).toHaveClass('text-muted')
    })

    it('lists the caveats and what to ask next', async () => {
      renderReport(makeMission('done', { report: makeReport() }))
      await headline()
      expect(within(screen.getByRole('region', { name: 'Caveats' })).getAllByRole('listitem')).toHaveLength(1)
      const next = within(screen.getByRole('region', { name: 'Ask next' })).getAllByRole('listitem')
      expect(next.map((item) => item.textContent)).toEqual(['Does it hold over two years?', 'Is there a weekday effect?'])
    })

    it('leaves out every section the report has nothing for', async () => {
      renderReport(makeMission('done', { report: makeReport({ stats: [], keyArtifactIds: [], steps: [], caveats: [], nextQuestions: [] }) }))
      await headline()
      expect(screen.queryByRole('region')).not.toBeInTheDocument()
      expect(screen.queryByRole('definition')).not.toBeInTheDocument()
      expect(screen.queryByTestId('artifact')).not.toBeInTheDocument()
    })

    it('signs off with the castle mark', async () => {
      renderReport(makeMission('done', { report: makeReport() }))
      await headline()
      expect(within(screen.getByRole('contentinfo')).getByRole('img', { name: 'kingdom' })).toBeInTheDocument()
    })

    describe('actions', () => {
      it('is a slim row with one filled button and no way back, since the tabs do that', async () => {
        const { container } = renderReport(makeMission('done', { report: makeReport() }))
        await headline()
        const actions = within(screen.getByRole('group', { name: 'Report actions' }))
        expect(actions.getAllByRole('button').map((button) => button.textContent)).toEqual(['Copy link', 'Regenerate', 'Export PDF'])
        expect(screen.queryByRole('link', { name: /back to mission/i })).not.toBeInTheDocument()
        const filled = container.querySelectorAll('[class*="bg-ink"]')
        expect(filled).toHaveLength(1)
        expect(filled[0]).toHaveTextContent('Export PDF')
        expect(screen.getByRole('group', { name: 'Report actions' })).toHaveClass('print:hidden')
      })

      it('copies the address of the report and says so for a moment', async () => {
        const { user } = renderReport(makeMission('done', { report: makeReport() }))
        await headline()
        await user.click(screen.getByRole('button', { name: 'Copy link' }))
        expect(await navigator.clipboard.readText()).toBe(window.location.href)
        expect(screen.getByRole('button', { name: 'Copied' })).toBeInTheDocument()
        await act(() => vi.advanceTimersByTimeAsync(2000))
        expect(screen.getByRole('button', { name: 'Copy link' })).toBeInTheDocument()
      })

      it('stays as it is when the clipboard is out of reach', async () => {
        renderReport(makeMission('done', { report: makeReport() }))
        await headline()
        vi.stubGlobal('navigator', { ...navigator, clipboard: undefined })
        fireEvent.click(screen.getByRole('button', { name: 'Copy link' }))
        await act(() => vi.advanceTimersByTimeAsync(0))
        expect(screen.getByRole('button', { name: 'Copy link' })).toBeInTheDocument()
        vi.unstubAllGlobals()
      })

      it('prints the page to export a PDF', async () => {
        const print = vi.fn()
        vi.stubGlobal('print', print)
        const { user } = renderReport(makeMission('done', { report: makeReport() }))
        await headline()
        await user.click(screen.getByRole('button', { name: 'Export PDF' }))
        expect(print).toHaveBeenCalledTimes(1)
        vi.unstubAllGlobals()
      })

      it('asks Devin to rewrite the report once, keeps the old one in view, then shows the new one', async () => {
        const mission = makeMission('done', { report: makeReport() })
        const { generateReport, user } = renderReport(mission)
        await headline()
        await user.dblClick(screen.getByRole('button', { name: 'Regenerate' }))
        expect(generateReport).toHaveBeenCalledExactlyOnceWith(mission.id)

        const busy = await screen.findByRole('button', { name: 'Rewriting' })
        expect(busy).toHaveAttribute('aria-disabled', 'true')
        expect(screen.getByRole('heading', { level: 2, name: 'Wind leads dust by two days' })).toBeInTheDocument()
        await user.click(busy)
        expect(generateReport).toHaveBeenCalledTimes(1)

        await act(() => vi.advanceTimersByTimeAsync(STEP_MS))
        expect(await screen.findByRole('button', { name: 'Regenerate' })).toBeInTheDocument()
        expect(screen.queryByRole('heading', { level: 2, name: 'Wind leads dust by two days' })).not.toBeInTheDocument()
      })
    })
  })

  describe('without a report', () => {
    const generate = () => screen.findByRole('button', { name: 'Generate report' })

    it.each(['working', 'waiting', 'done'] as const)('invites you to generate one for a %s mission, and asks once', async (status) => {
      const mission = makeMission(status)
      const { generateReport, user, container } = renderReport(mission)
      expect(await screen.findByRole('heading', { level: 2, name: 'Write up the mission' })).toBeInTheDocument()
      expect(container.querySelector('[class*="bg-ink"]')).toBeNull()
      await user.dblClick(await generate())
      expect(generateReport).toHaveBeenCalledExactlyOnceWith(mission.id)
    })

    it('goes from the invitation to the writing state to the report', async () => {
      const { user } = renderReport(makeMission('waiting'))
      await user.click(await generate())
      expect(await screen.findByRole('status')).toHaveTextContent('Devin is writing the report')
      expect(screen.queryByRole('button', { name: 'Generate report' })).not.toBeInTheDocument()
      expect(screen.getByRole('link', { name: 'Report, in progress' })).toBeInTheDocument()

      await act(() => vi.advanceTimersByTimeAsync(STEP_MS))
      expect(await screen.findByRole('group', { name: 'Report actions' })).toBeInTheDocument()
      expect(screen.queryByRole('status')).not.toBeInTheDocument()
    })

    it('shows the writing state while the request itself is in flight', async () => {
      const { generateReport, user } = renderReport(makeMission('waiting'))
      let finish = () => {}
      generateReport.mockImplementationOnce(() => new Promise<void>((resolve) => (finish = resolve)))
      await user.click(await generate())
      expect(screen.getByRole('status')).toHaveTextContent('Devin is writing the report')
      await act(async () => finish())
    })

    it('shows the writing state for a report that was already on its way', async () => {
      renderReport(makeMission('working', { reportPending: true }))
      expect(await screen.findByRole('status')).toHaveTextContent('Devin is writing the report')
      expect(screen.getByText(/keep using the thread/)).toHaveClass('text-muted')
    })

    it('lets you try again when the request fails', async () => {
      const { generateReport, user } = renderReport(makeMission('waiting'))
      generateReport.mockRejectedValueOnce(new TypeError('Failed to fetch'))
      await user.click(await generate())
      await user.click(await generate())
      expect(generateReport).toHaveBeenCalledTimes(2)
    })

    it('offers a report on a failed mission that did reach a conclusion', async () => {
      renderReport(makeMission('failed', { events: makeMission('waiting').events }))
      expect(await generate()).toBeInTheDocument()
    })

    it('has nothing to report on when a failed mission never concluded', async () => {
      renderReport(makeMission('failed'))
      expect(await screen.findByRole('heading', { level: 2, name: 'Nothing to report on yet' })).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'Generate report' })).not.toBeInTheDocument()
    })

    it('has nothing to report on before Devin has done anything', async () => {
      const asked = makeMission('working')
      renderReport({ ...asked, events: [asked.events[0], { id: 'x', at: asked.createdAt, kind: 'error', text: 'Devin could not be reached' }] })
      expect(await screen.findByRole('heading', { level: 2, name: 'Nothing to report on yet' })).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'Generate report' })).not.toBeInTheDocument()
    })
  })

  it('shows not found for an unknown mission', async () => {
    renderReport(makeMission('done'), 'nope')
    expect(await screen.findByRole('heading', { name: 'Mission not found' })).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Mission views' })).not.toBeInTheDocument()
  })
})
