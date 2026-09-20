import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMockApi } from '../../api/mock'
import { makeMission, makeReport } from '../../test/missions'
import { renderWithApp } from '../../test/render'
import type { Mission } from '../../types'
import { MissionHeader } from './MissionHeader'

function renderHeader(mission: Mission, reconnecting = false) {
  const api = createMockApi({ seed: { missions: [mission], datasets: [] } })
  const markDone = vi.spyOn(api, 'markDone')
  const generateReport = vi.spyOn(api, 'generateReport')
  const { container } = renderWithApp(<MissionHeader mission={mission} reconnecting={reconnecting} />, { api })
  return { markDone, generateReport, container, user: userEvent.setup({ advanceTimers: vi.advanceTimersByTime }) }
}

describe('MissionHeader', () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }))
  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
  })

  it.each([
    ['working', 'Working', 'Devin is working'],
    ['waiting', 'Waiting for you', 'Waiting for you'],
    ['done', 'Done', 'Done'],
    ['failed', 'Failed', 'Failed'],
  ] as const)('titles a %s mission with its dot and status text', (status, dot, text) => {
    renderHeader(makeMission(status, { title: 'Storm damage vs outages' }))
    expect(screen.getByRole('heading', { name: 'Storm damage vs outages' })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: dot })).toBeInTheDocument()
    expect(screen.getByText(text)).toHaveClass('text-muted')
  })

  it('says it is reconnecting instead of the status while reads fail', () => {
    renderHeader(makeMission('working'), true)
    expect(screen.getByText('Reconnecting')).toBeInTheDocument()
    expect(screen.queryByText('Devin is working')).not.toBeInTheDocument()
  })

  it('links out to the Devin session in a new tab', () => {
    renderHeader(makeMission('working', { sessionUrl: 'https://app.devin.ai/sessions/devin-abc' }))
    const link = screen.getByRole('link', { name: 'Open in Devin' })
    expect(link).toHaveAttribute('href', 'https://app.devin.ai/sessions/devin-abc')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noreferrer')
  })

  it('has no Devin link without a session', () => {
    renderHeader(makeMission('working'))
    expect(screen.queryByRole('link', { name: 'Open in Devin' })).not.toBeInTheDocument()
  })

  it.each(['working', 'waiting', 'failed'] as const)('marks a %s mission done', async (status) => {
    const mission = makeMission(status)
    const { markDone, user } = renderHeader(mission)
    await user.click(screen.getByRole('button', { name: 'Mark done' }))
    expect(markDone).toHaveBeenCalledExactlyOnceWith(mission.id)
  })

  it('asks only once while the first request is in flight', async () => {
    const { markDone, user } = renderHeader(makeMission('waiting'))
    let finish = () => {}
    markDone.mockImplementationOnce(() => new Promise<void>((resolve) => (finish = resolve)))
    await user.dblClick(screen.getByRole('button', { name: 'Mark done' }))
    expect(markDone).toHaveBeenCalledTimes(1)
    finish()
  })

  it('lets you try again when marking done fails', async () => {
    const mission = makeMission('waiting')
    const { markDone, user } = renderHeader(mission)
    markDone.mockRejectedValueOnce(new TypeError('Failed to fetch'))
    await user.click(screen.getByRole('button', { name: 'Mark done' }))
    await user.click(screen.getByRole('button', { name: 'Mark done' }))
    expect(markDone).toHaveBeenCalledTimes(2)
  })

  it('hides Mark done once the mission is done', () => {
    renderHeader(makeMission('done'))
    expect(screen.queryByRole('button', { name: 'Mark done' })).not.toBeInTheDocument()
  })

  describe('report control', () => {
    const generate = () => screen.getByRole('button', { name: 'Generate report' })

    it.each(['working', 'waiting', 'done'] as const)('offers a report on a %s mission and asks for it once', async (status) => {
      const mission = makeMission(status)
      const { generateReport, user } = renderHeader(mission)
      await user.click(generate())
      expect(generateReport).toHaveBeenCalledExactlyOnceWith(mission.id)
    })

    it('offers a report on a failed mission that did reach a conclusion', () => {
      renderHeader(makeMission('failed', { events: makeMission('waiting').events }))
      expect(generate()).toBeInTheDocument()
    })

    it('has nothing to report on when a failed mission never concluded', () => {
      renderHeader(makeMission('failed'))
      expect(screen.queryByRole('button', { name: 'Generate report' })).not.toBeInTheDocument()
    })

    it('has nothing to report on before Devin has done anything', () => {
      const asked = makeMission('working')
      renderHeader({
        ...asked,
        events: [asked.events[0], { id: 'x', at: asked.createdAt, kind: 'error', text: 'Devin could not be reached' }],
      })
      expect(screen.queryByRole('button', { name: 'Generate report' })).not.toBeInTheDocument()
    })

    it('is busy and asks only once while the request is in flight', async () => {
      const { generateReport, user } = renderHeader(makeMission('waiting'))
      let finish = () => {}
      generateReport.mockImplementationOnce(() => new Promise<void>((resolve) => (finish = resolve)))
      await user.dblClick(generate())
      expect(generateReport).toHaveBeenCalledTimes(1)
      expect(screen.getByRole('button', { name: 'Writing report' })).toHaveAttribute('aria-busy', 'true')
      finish()
    })

    it('says the report is being written while one is pending, and cannot be clicked', async () => {
      const { generateReport, user } = renderHeader(makeMission('working', { reportPending: true }))
      const busy = screen.getByRole('button', { name: 'Writing report' })
      expect(busy).toHaveAttribute('aria-busy', 'true')
      expect(busy).toHaveAttribute('aria-disabled', 'true')
      await user.click(busy)
      expect(generateReport).not.toHaveBeenCalled()
      expect(screen.queryByRole('button', { name: 'Generate report' })).not.toBeInTheDocument()
    })

    it('lets you try again when the request fails', async () => {
      const { generateReport, user } = renderHeader(makeMission('waiting'))
      generateReport.mockRejectedValueOnce(new TypeError('Failed to fetch'))
      await user.click(generate())
      await user.click(generate())
      expect(generateReport).toHaveBeenCalledTimes(2)
    })

    it('links to the report once there is one, instead of offering to write it', () => {
      renderHeader(makeMission('done', { id: 'm 1', report: makeReport() }))
      expect(screen.getByRole('link', { name: 'View report' })).toHaveAttribute('href', '/missions/m%201/report')
      expect(screen.queryByRole('button', { name: 'Generate report' })).not.toBeInTheDocument()
    })

    it('keeps the link to the last report while a new one is being written', () => {
      renderHeader(makeMission('working', { report: makeReport(), reportPending: true }))
      expect(screen.getByRole('link', { name: 'View report' })).toHaveAttribute('aria-busy', 'true')
      expect(screen.queryByRole('button', { name: 'Writing report' })).not.toBeInTheDocument()
    })

    it('shortens its label on phones and leaves the one filled button to the page', () => {
      const { container } = renderHeader(makeMission('waiting'))
      expect(within(generate()).getByText('Report')).toHaveClass('sm:hidden')
      expect(within(generate()).getByText('Generate report')).toHaveClass('max-sm:hidden')
      expect(container.querySelector('[class*="bg-ink"]')).toBeNull()
    })
  })
})
