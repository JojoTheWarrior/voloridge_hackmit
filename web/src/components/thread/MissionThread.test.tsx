import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMockApi } from '../../api/mock'
import { makeMission } from '../../test/missions'
import { renderWithApp } from '../../test/render'
import { MissionThread } from './MissionThread'

describe('MissionThread live activity', () => {
  it('shows a persistent running indicator even before the first progress event', () => {
    const mission = makeMission('working', { events: [] })
    renderWithApp(<MissionThread mission={mission} />)
    expect(screen.getByRole('status', { name: 'Research progress' })).toHaveTextContent('Research in progress')
    expect(screen.getByText('Updates and results will appear here as Devin works.')).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Reply to Devin' })).toBeEnabled()
  })

  it('keeps real progress and artifacts visible while working and shows the latest update', () => {
    const at = '2026-09-20T12:00:00Z'
    const mission = makeMission('working', { events: [
      { id: 's1', at, kind: 'step', stepId: 's1', state: 'active', label: 'Compare seasonal baselines' },
      { id: 't1', at, kind: 'thought', text: 'Both sources cover the same three years.' },
      { id: 'a1', at, kind: 'artifact', artifact: { id: 'a1', type: 'stats', title: 'Coverage', items: [{ label: 'Years', value: '3' }] } },
    ] })
    renderWithApp(<MissionThread mission={mission} />)
    const thread = within(screen.getByRole('log', { name: 'Mission thread' }))
    expect(thread.getByText('Compare seasonal baselines')).toBeVisible()
    expect(thread.getByText('Both sources cover the same three years.')).toBeVisible()
    expect(thread.getByText('Years')).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Show the work' })).not.toBeInTheDocument()
    const progress = screen.getByRole('status', { name: 'Research progress' })
    expect(progress).toHaveTextContent('Latest step: Compare seasonal baselines')
    expect(progress.querySelector('time')).toHaveAttribute('datetime', at)
  })

  it.each(['working', 'done'] as const)('sends steering or follow-up messages when %s', async (status) => {
    const mission = makeMission(status, { events: [] })
    const api = createMockApi({ seed: { missions: [mission], datasets: [] } })
    const send = vi.spyOn(api, 'sendMessage').mockResolvedValue(undefined)
    renderWithApp(<MissionThread mission={mission} />, { api })
    await userEvent.setup().type(screen.getByRole('textbox', { name: 'Reply to Devin' }), 'Focus on dry years{Enter}')
    expect(send).toHaveBeenCalledExactlyOnceWith(mission.id, 'Focus on dry years')
    if (status === 'done') expect(screen.queryByRole('status', { name: 'Research progress' })).not.toBeInTheDocument()
  })
})
