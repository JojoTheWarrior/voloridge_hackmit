import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMockApi } from '../../api/mock'
import { makeMission } from '../../test/missions'
import { renderWithApp } from '../../test/render'
import type { Mission } from '../../types'
import { MissionHeader } from './MissionHeader'

function renderHeader(mission: Mission, reconnecting = false) {
  const api = createMockApi({ seed: { missions: [mission], datasets: [] } })
  const markDone = vi.spyOn(api, 'markDone')
  renderWithApp(<MissionHeader mission={mission} reconnecting={reconnecting} />, { api })
  return { markDone, user: userEvent.setup({ advanceTimers: vi.advanceTimersByTime }) }
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
})
