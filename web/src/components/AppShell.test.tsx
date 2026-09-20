import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { createMockApi } from '../api/mock'
import { renderWithApp } from '../test/render'
import { AppShell } from './AppShell'

function renderShell() {
  return renderWithApp(
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<p>home page</p>} />
        <Route path="datasets" element={<p>datasets page</p>} />
      </Route>
    </Routes>,
    { api: createMockApi({ seed: { missions: [], datasets: [] } }) },
  )
}

describe('AppShell', () => {
  it('renders the routed page beside the sidebar', async () => {
    renderShell()
    expect(screen.getByText('home page')).toBeInTheDocument()
    expect(await screen.findByRole('navigation', { name: 'Main' })).toBeInTheDocument()
  })

  it('opens the slide-over menu and closes it on Escape', async () => {
    const user = userEvent.setup()
    renderShell()
    await user.click(screen.getByRole('button', { name: 'Open menu' }))
    expect(screen.getAllByRole('navigation', { name: 'Main' })).toHaveLength(2)
    await user.keyboard('{Escape}')
    expect(screen.getAllByRole('navigation', { name: 'Main' })).toHaveLength(1)
  })

  it('closes the menu from the scrim', async () => {
    const user = userEvent.setup()
    renderShell()
    await user.click(screen.getByRole('button', { name: 'Open menu' }))
    await user.click(screen.getByRole('button', { name: 'Close menu' }))
    expect(screen.queryByRole('button', { name: 'Close menu' })).not.toBeInTheDocument()
  })

  it('closes the menu after navigating from it', async () => {
    const user = userEvent.setup()
    renderShell()
    await user.click(screen.getByRole('button', { name: 'Open menu' }))
    await user.click(screen.getAllByRole('link', { name: 'Datasets' })[1])
    expect(screen.getByText('datasets page')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Close menu' })).not.toBeInTheDocument()
  })
})
