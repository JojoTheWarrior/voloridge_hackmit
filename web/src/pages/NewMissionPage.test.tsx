import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes, useParams } from 'react-router-dom'
import { seedDatasets } from '../api/fixtures'
import { EXAMPLE_PROMPTS, STARTER_IDEAS } from '../examples'
import { createMockApi } from '../api/mock'
import { renderWithApp } from '../test/render'
import { NewMissionPage } from './NewMissionPage'

function MissionProbe() {
  return <p>mission {useParams().id}</p>
}

function renderPage(datasets = seedDatasets()) {
  const api = createMockApi({ seed: { missions: [], datasets } })
  const createMission = vi.spyOn(api, 'createMission')
  renderWithApp(
    <Routes>
      <Route index element={<NewMissionPage />} />
      <Route path="missions/:id" element={<MissionProbe />} />
    </Routes>,
    { api },
  )
  return { api, createMission, user: userEvent.setup({ advanceTimers: vi.advanceTimersByTime }) }
}

const prompt = () => screen.getByRole('textbox', { name: 'Mission prompt' })

describe('NewMissionPage', () => {
  // A created mission starts ticking; fake timers keep that from outliving the test.
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }))
  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
  })

  it('asks the question and focuses the prompt', () => {
    renderPage()
    expect(screen.getByRole('heading', { name: 'What should we look into?' })).toBeInTheDocument()
    expect(prompt()).toHaveFocus()
  })

  it('submits on Enter and opens the new mission', async () => {
    const { createMission, user } = renderPage()
    await user.type(prompt(), 'Does wind move PM2.5?{Enter}')
    expect(await screen.findByText('mission m-1')).toBeInTheDocument()
    expect(createMission).toHaveBeenCalledWith({
      hypothesis: 'Does wind move PM2.5?',
      datasetIds: seedDatasets().map((d) => d.id),
    })
  })

  it('submits from the button', async () => {
    const { user } = renderPage()
    await user.type(prompt(), 'A leads B')
    await user.click(screen.getByRole('button', { name: 'Start mission' }))
    expect(await screen.findByText('mission m-1')).toBeInTheDocument()
  })

  it('inserts a newline on Shift+Enter without submitting', async () => {
    const { createMission, user } = renderPage()
    await user.type(prompt(), 'line one{Shift>}{Enter}{/Shift}line two')
    expect(prompt()).toHaveValue('line one\nline two')
    expect(createMission).not.toHaveBeenCalled()
  })

  it.each(['{Enter}', '   {Enter}'])('ignores a blank prompt (%j)', async (keys) => {
    const { createMission, user } = renderPage()
    await user.type(prompt(), keys)
    await user.click(screen.getByRole('button', { name: 'Start mission' }))
    expect(createMission).not.toHaveBeenCalled()
    expect(screen.getByRole('heading', { name: 'What should we look into?' })).toBeInTheDocument()
  })

  it('submits only once when Enter is pressed twice quickly', async () => {
    const { createMission, user } = renderPage()
    await user.type(prompt(), 'A leads B{Enter}{Enter}')
    await screen.findByText('mission m-1')
    expect(createMission).toHaveBeenCalledTimes(1)
  })

  it('fills the prompt from an example and focuses it', async () => {
    const { createMission, user } = renderPage()
    await screen.findByRole('button', { name: 'PUDL power generation' })
    await user.click(screen.getByRole('button', { name: EXAMPLE_PROMPTS[1] }))
    expect(prompt()).toHaveValue(EXAMPLE_PROMPTS[1])
    expect(prompt()).toHaveFocus()
    expect(createMission).not.toHaveBeenCalled()
    expect(screen.getAllByRole('button', { pressed: true }).map((button) => button.textContent)).toEqual(['PUDL power generation', 'Global Water Watch', 'Open-Meteo weather'])
    await user.click(screen.getByRole('button', { name: 'More ideas' }))
    expect(screen.getByRole('button', { name: STARTER_IDEAS[3].text })).toBeInTheDocument()
    expect(prompt()).toHaveValue(EXAMPLE_PROMPTS[1])
    await user.click(screen.getByRole('button', { name: 'Start mission' }))
    await waitFor(() => expect(createMission).toHaveBeenCalled())
    expect(createMission.mock.calls[0][0].datasetIds).toEqual(['pudl', 'global-water-watch', 'open-meteo'])
  })

  it('selects every dataset by default and drops the ones toggled off', async () => {
    const { createMission, user } = renderPage()
    const chips = await screen.findAllByRole('button', { pressed: true })
    expect(chips).toHaveLength(6)

    await user.click(screen.getByRole('button', { name: 'Sentinel-2 imagery' }))
    expect(screen.getByRole('button', { name: 'Sentinel-2 imagery' })).toHaveAttribute('aria-pressed', 'false')

    await user.type(prompt(), 'A leads B{Enter}')
    await waitFor(() => expect(createMission).toHaveBeenCalled())
    expect(createMission.mock.calls[0][0].datasetIds).toEqual(['pudl', 'global-water-watch', 'viirs', 'openstreetmap', 'open-meteo'])
  })

  it('re-selects a dataset toggled twice', async () => {
    const { user } = renderPage()
    const chip = await screen.findByRole('button', { name: 'PUDL power generation' })
    await user.click(chip)
    await user.click(chip)
    expect(chip).toHaveAttribute('aria-pressed', 'true')
  })

  it('works with no datasets linked', async () => {
    const { createMission, user } = renderPage([])
    await user.type(prompt(), 'A leads B{Enter}')
    await screen.findByText('mission m-1')
    expect(createMission.mock.calls[0][0].datasetIds).toEqual([])
    expect(screen.queryByRole('button', { pressed: true })).not.toBeInTheDocument()
  })

  it('preserves the prompt after a failed request and lets the user retry', async () => {
    const { createMission, user } = renderPage()
    createMission.mockRejectedValueOnce(new Error('offline'))
    await user.type(prompt(), 'A leads B{Enter}')
    expect(await screen.findByRole('alert')).toHaveTextContent('Couldn’t start the mission')
    expect(prompt()).toHaveValue('A leads B')
    await user.click(screen.getByRole('button', { name: 'Start mission' }))
    expect(await screen.findByText('mission m-1')).toBeInTheDocument()
    expect(createMission).toHaveBeenCalledTimes(2)
  })

  it('searches research and attaches the complete finding to the new mission', async () => {
    const { api, createMission, user } = renderPage()
    vi.spyOn(api, 'listResearch').mockResolvedValue([
      { id: 'dams/0', title: 'Reservoirs under stress', summary: 'Look at storage', source: 'dams', verdict: 'partial', reference: 'Full evidence and caveats' },
      { id: 'air/0', title: 'Air quality', summary: 'Pollution', source: 'air', verdict: 'partial', reference: 'Other evidence' },
    ])
    await user.click(screen.getByRole('button', { name: 'Attach research' }))
    await user.type(await screen.findByRole('textbox', { name: 'Search research' }), 'reservoir')
    await user.click(await screen.findByRole('button', { name: /Reservoirs under stress/ }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(prompt()).toHaveValue('Investigate: Reservoirs under stress')
    await user.click(screen.getByRole('button', { name: 'Start mission' }))
    await screen.findByText('mission m-1')
    expect(createMission.mock.calls[0][0].reference).toBe('Full evidence and caveats')
  })

  it('attaches pasted notes without replacing a written question, and removes them', async () => {
    const { createMission, user } = renderPage()
    await user.type(prompt(), 'My question')
    await user.click(screen.getByRole('button', { name: 'Attach research' }))
    await user.click(screen.getByRole('button', { name: 'Paste notes' }))
    await user.type(screen.getByRole('textbox', { name: 'Notes, findings, or source links' }), 'Prior evidence')
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Attach research' }))
    expect(prompt()).toHaveValue('My question')
    await user.click(screen.getByRole('button', { name: 'Remove research' }))
    await user.click(screen.getByRole('button', { name: 'Start mission' }))
    await screen.findByText('mission m-1')
    expect(createMission.mock.calls[0][0]).not.toHaveProperty('reference')
  })

  it('recovers a failed library load', async () => {
    const { api, user } = renderPage()
    vi.spyOn(api, 'listResearch').mockRejectedValueOnce(new Error('offline')).mockResolvedValue([])
    await user.click(screen.getByRole('button', { name: 'Attach research' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('library couldn’t load')
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('status')).toHaveTextContent('No research in the library yet')
  })
})
