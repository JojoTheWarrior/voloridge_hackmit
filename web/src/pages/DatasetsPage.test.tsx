import { cleanup, screen, within } from '@testing-library/react'
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

const VIEW_KEY = 'kingdom.datasets.view'

const rows = () => within(screen.getByRole('table')).getAllByRole('row').slice(1)
const cards = () => within(screen.getByRole('list', { name: 'Datasets' })).getAllByRole('listitem')
const listToggle = () => screen.getByRole('button', { name: 'List view' })
const cardToggle = () => screen.getByRole('button', { name: 'Card view' })

async function openDialog(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole('button', { name: 'Link dataset' }))
  return screen.getByRole('dialog', { name: 'Link a dataset' })
}

beforeEach(() => localStorage.clear())

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

describe('DatasetsPage view toggle', () => {
  it('starts in list view', async () => {
    renderPage()
    await screen.findByRole('table')
    expect(screen.queryByRole('list', { name: 'Datasets' })).not.toBeInTheDocument()
    expect(listToggle()).toHaveAttribute('aria-pressed', 'true')
    expect(cardToggle()).toHaveAttribute('aria-pressed', 'false')
  })

  it('shows one card per dataset in card view', async () => {
    const { user } = renderPage()
    await user.click(await screen.findByRole('button', { name: 'Card view' }))

    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(cardToggle()).toHaveAttribute('aria-pressed', 'true')
    expect(listToggle()).toHaveAttribute('aria-pressed', 'false')
    expect(cards()).toHaveLength(4)

    const first = within(cards()[0])
    expect(first.getByText('GDELT events')).toBeInTheDocument()
    expect(first.getByText('42')).toHaveClass('font-mono')
    expect(first.getByText('Mar 2025 – Sep 2026')).toBeInTheDocument()
    expect(first.getByText('synced 2h ago')).toBeInTheDocument()
    const link = first.getByRole('link', { name: 'gdeltproject.org' })
    expect(link).toHaveAttribute('href', 'https://www.gdeltproject.org')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noreferrer')
    expect(within(cards()[3]).getByText('synced 1d ago')).toBeInTheDocument()
  })

  it('gives every card a decorative thumbnail', async () => {
    const { user } = renderPage()
    await user.click(await screen.findByRole('button', { name: 'Card view' }))
    for (const card of cards()) expect(card.querySelector('svg[aria-hidden="true"]')).toBeInTheDocument()
  })

  it('switches back to the table', async () => {
    const { user } = renderPage()
    await user.click(await screen.findByRole('button', { name: 'Card view' }))
    await user.click(listToggle())
    expect(rows()).toHaveLength(4)
    expect(screen.queryByRole('list', { name: 'Datasets' })).not.toBeInTheDocument()
    expect(listToggle()).toHaveAttribute('aria-pressed', 'true')
  })

  it('remembers the view across visits', async () => {
    const { user } = renderPage()
    await user.click(await screen.findByRole('button', { name: 'Card view' }))
    expect(localStorage.getItem(VIEW_KEY)).toBe('card')
    cleanup()

    renderPage()
    await screen.findByRole('list', { name: 'Datasets' })
    expect(screen.queryByRole('table')).not.toBeInTheDocument()

    await user.click(listToggle())
    expect(localStorage.getItem(VIEW_KEY)).toBe('list')
    cleanup()

    renderPage()
    expect(await screen.findByRole('table')).toBeInTheDocument()
  })

  it.each(['grid', '', 'CARD', '{"view":"card"}'])('falls back to list view for the stored value %j', async (stored) => {
    localStorage.setItem(VIEW_KEY, stored)
    renderPage()
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(listToggle()).toHaveAttribute('aria-pressed', 'true')
  })

  describe('when storage is blocked', () => {
    beforeEach(() => {
      const denied = () => {
        throw new DOMException('denied', 'SecurityError')
      }
      vi.spyOn(Storage.prototype, 'getItem').mockImplementation(denied)
      vi.spyOn(Storage.prototype, 'setItem').mockImplementation(denied)
    })
    afterEach(() => vi.restoreAllMocks())

    it('still renders and switches views', async () => {
      const { user } = renderPage()
      expect(await screen.findByRole('table')).toBeInTheDocument()
      await user.click(cardToggle())
      expect(cards()).toHaveLength(4)
      await user.click(listToggle())
      expect(rows()).toHaveLength(4)
    })
  })

  it('has no toggle in the empty state', async () => {
    localStorage.setItem(VIEW_KEY, 'card')
    renderPage([])
    await screen.findByRole('heading', { name: 'Link your first dataset' })
    expect(screen.queryByRole('button', { name: 'List view' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Card view' })).not.toBeInTheDocument()
    expect(screen.queryByRole('list', { name: 'Datasets' })).not.toBeInTheDocument()
  })

  it('adds a linked dataset as the first card', async () => {
    const { api, user } = renderPage()
    await user.click(await screen.findByRole('button', { name: 'Card view' }))
    const dialog = await openDialog(user)
    await user.type(within(dialog).getByLabelText('Name'), 'FRED')
    await user.type(within(dialog).getByLabelText('URL'), 'https://fred.stlouisfed.org/series/DCOILBRENTEU{Enter}')

    expect(cards()).toHaveLength(5)
    const first = within(cards()[0])
    expect(first.getByText('FRED')).toBeInTheDocument()
    expect(first.getByRole('link', { name: 'fred.stlouisfed.org' })).toBeInTheDocument()
    expect(first.getByText('0')).toBeInTheDocument()
    expect(first.getByText('—')).toBeInTheDocument()
    expect(first.getByText('synced just now')).toBeInTheDocument()
    expect((await api.listDatasets())[0].kind).toBe('other')
  })
})
