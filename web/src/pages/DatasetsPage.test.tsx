import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { seedDatasets } from '../api/fixtures'
import { createMockApi } from '../api/mock'
import { renderWithApp } from '../test/render'
import { DatasetsPage } from './DatasetsPage'

function renderPage(datasets = seedDatasets()) {
  const api = createMockApi({ seed: { missions: [], datasets } })
  renderWithApp(<DatasetsPage />, { api })
  return { api, user: userEvent.setup() }
}

const rows = () => within(screen.getByRole('table')).getAllByRole('row').slice(1)

async function openDialog(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole('button', { name: 'Link dataset' }))
  return screen.getByRole('dialog', { name: 'Link a dataset' })
}

describe('DatasetsPage', () => {
  it('lists linked datasets with their source host', async () => {
    renderPage()
    await screen.findByRole('table')
    expect(rows()).toHaveLength(4)
    const first = within(rows()[0])
    expect(first.getByText('GDELT events')).toBeInTheDocument()
    expect(first.getByText('42')).toBeInTheDocument()
    const link = first.getByRole('link', { name: 'gdeltproject.org' })
    expect(link).toHaveAttribute('href', 'https://www.gdeltproject.org')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noreferrer')
  })

  it('links a dataset and shows it first', async () => {
    const { user } = renderPage()
    const dialog = await openDialog(user)
    await user.type(within(dialog).getByLabelText('Name'), 'FRED')
    await user.type(within(dialog).getByLabelText('URL'), 'https://fred.stlouisfed.org/series/DCOILBRENTEU')
    await user.click(within(dialog).getByRole('button', { name: 'Link dataset' }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(rows()).toHaveLength(5)
    expect(within(rows()[0]).getByText('FRED')).toBeInTheDocument()
    expect(within(rows()[0]).getByRole('link', { name: 'fred.stlouisfed.org' })).toBeInTheDocument()
    expect(within(rows()[0]).getByText('just now')).toBeInTheDocument()
  })

  it('submits the dialog with Enter', async () => {
    const { user } = renderPage()
    const dialog = await openDialog(user)
    await user.type(within(dialog).getByLabelText('Name'), 'FRED')
    await user.type(within(dialog).getByLabelText('URL'), 'https://fred.stlouisfed.org{Enter}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(rows()).toHaveLength(5)
  })

  it('asks for a name', async () => {
    const { user } = renderPage()
    const dialog = await openDialog(user)
    await user.type(within(dialog).getByLabelText('URL'), 'https://x.com')
    await user.click(within(dialog).getByRole('button', { name: 'Link dataset' }))
    expect(within(dialog).getByText('Enter a name')).toBeInTheDocument()
    expect(within(dialog).getByLabelText('Name')).toBeInvalid()
    expect(rows()).toHaveLength(4)
  })

  it.each(['ftp://x.com', 'not a url'])('rejects the url %j and clears the error on edit', async (url) => {
    const { user } = renderPage()
    const dialog = await openDialog(user)
    await user.type(within(dialog).getByLabelText('Name'), 'Thing')
    await user.type(within(dialog).getByLabelText('URL'), url)
    await user.click(within(dialog).getByRole('button', { name: 'Link dataset' }))
    expect(within(dialog).getByText('Enter an http or https URL')).toBeInTheDocument()
    expect(within(dialog).getByLabelText('URL')).toBeInvalid()

    await user.type(within(dialog).getByLabelText('URL'), 'x')
    expect(within(dialog).queryByText('Enter an http or https URL')).not.toBeInTheDocument()
  })

  it('resets the form when cancelled', async () => {
    const { user } = renderPage()
    let dialog = await openDialog(user)
    await user.type(within(dialog).getByLabelText('Name'), 'Half typed')
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    dialog = await openDialog(user)
    expect(within(dialog).getByLabelText('Name')).toHaveValue('')
    expect(rows()).toHaveLength(4)
  })

  it('invites you to link the first dataset when there are none', async () => {
    const { user } = renderPage([])
    expect(await screen.findByRole('heading', { name: 'Link your first dataset' })).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Link dataset' })).toHaveLength(1)

    const dialog = await openDialog(user)
    await user.type(within(dialog).getByLabelText('Name'), 'First')
    await user.type(within(dialog).getByLabelText('URL'), 'https://first.dev{Enter}')
    expect(rows()).toHaveLength(1)
  })

  it('shows a dash for a dataset with no range yet', async () => {
    renderPage([{ id: 'x', name: 'Fresh', url: 'https://fresh.dev', kind: 'other', seriesCount: 0, dateRange: '', syncedAt: new Date().toISOString() }])
    await screen.findByRole('table')
    expect(within(rows()[0]).getByText('—')).toBeInTheDocument()
  })
})
