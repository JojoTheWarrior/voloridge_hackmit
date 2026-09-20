import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes, useParams } from 'react-router-dom'
import { seedDatasets } from '../api/fixtures'
import { EXAMPLE_PROMPTS } from '../examples'
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
    await user.click(screen.getByRole('button', { name: EXAMPLE_PROMPTS[1] }))
    expect(prompt()).toHaveValue(EXAMPLE_PROMPTS[1])
    expect(prompt()).toHaveFocus()
    expect(createMission).not.toHaveBeenCalled()
  })

  it('selects every dataset by default and drops the ones toggled off', async () => {
    const { createMission, user } = renderPage()
    const chips = await screen.findAllByRole('button', { pressed: true })
    expect(chips).toHaveLength(4)

    await user.click(screen.getByRole('button', { name: 'Yahoo Finance' }))
    expect(screen.getByRole('button', { name: 'Yahoo Finance' })).toHaveAttribute('aria-pressed', 'false')

    await user.type(prompt(), 'A leads B{Enter}')
    await waitFor(() => expect(createMission).toHaveBeenCalled())
    expect(createMission.mock.calls[0][0].datasetIds).toEqual(['gdelt', 'open-meteo', 'cams'])
  })

  it('re-selects a dataset toggled twice', async () => {
    const { user } = renderPage()
    const chip = await screen.findByRole('button', { name: 'GDELT events' })
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
})
