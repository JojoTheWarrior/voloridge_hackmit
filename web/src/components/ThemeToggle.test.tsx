import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useTheme } from '../hooks/useTheme'
import { ThemeToggle } from './ThemeToggle'

function Reader() {
  return <output>{useTheme().theme}</output>
}

beforeEach(() => {
  localStorage.clear()
  delete document.documentElement.dataset.theme
})

describe('ThemeToggle', () => {
  it('names the mode it will switch to and flips on click', async () => {
    const user = userEvent.setup()
    render(<ThemeToggle />)
    await user.click(screen.getByRole('button', { name: 'Switch to dark mode' }))
    expect(document.documentElement.dataset.theme).toBe('dark')
    await user.click(screen.getByRole('button', { name: 'Switch to light mode' }))
    expect(document.documentElement.dataset.theme).toBe('light')
  })

  it('carries the rest of the app along', async () => {
    const user = userEvent.setup()
    render(
      <>
        <ThemeToggle />
        <Reader />
      </>,
    )
    expect(screen.getByRole('status')).toHaveTextContent('light')
    await user.click(screen.getByRole('button', { name: 'Switch to dark mode' }))
    expect(screen.getByRole('status')).toHaveTextContent('dark')
  })
})
