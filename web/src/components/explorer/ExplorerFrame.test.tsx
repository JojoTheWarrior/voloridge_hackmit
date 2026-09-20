import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { THEME_KEY } from '../../hooks/useTheme'
import { makeExplorer } from '../../test/missions'
import { ThemeToggle } from '../ThemeToggle'
import { ExplorerFrame } from './ExplorerFrame'

const SLOW_MS = 20_000
const explorer = makeExplorer()
const frame = () => screen.getByTitle<HTMLIFrameElement>(explorer.title)

function renderFrame(onRequestChange = vi.fn()) {
  return { onRequestChange, ...render(<ExplorerFrame explorer={explorer} onRequestChange={onRequestChange} />) }
}

describe('ExplorerFrame', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })
  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
  })

  it('frames the explorer in a sandbox that can run scripts and open links, and nothing more', () => {
    renderFrame()
    expect(frame()).toHaveAttribute('sandbox', 'allow-scripts allow-popups allow-popups-to-escape-sandbox')
    expect(frame().getAttribute('sandbox')).not.toContain('allow-same-origin')
    expect(frame()).toHaveAttribute('referrerpolicy', 'no-referrer')
    expect(frame()).toHaveAttribute('loading', 'eager')
    expect(frame()).toHaveAttribute('allow', 'fullscreen')
  })

  it.each(['light', 'dark'] as const)('tells the explorer to start in %s', (theme) => {
    localStorage.setItem(THEME_KEY, theme)
    renderFrame()
    expect(frame()).toHaveAttribute('src', `${explorer.src}?theme=${theme}`)
  })

  it('fills its area without a scrollbar of its own around it', () => {
    renderFrame()
    expect(frame()).toHaveClass('h-full', 'w-full')
    expect(frame().parentElement).toHaveClass('min-h-0', 'flex-1', 'border-t')
  })

  describe('theme messages', () => {
    const message = (theme: string) => [{ type: 'kingdom:theme', theme }, '*']

    it('posts the theme once the frame has loaded', () => {
      localStorage.setItem(THEME_KEY, 'dark')
      renderFrame()
      const post = vi.spyOn(frame().contentWindow!, 'postMessage')
      fireEvent.load(frame())
      expect(post.mock.calls).toEqual([message('dark')])
    })

    it('posts again whenever the theme changes, without reloading the frame', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      render(
        <>
          <ThemeToggle />
          <ExplorerFrame explorer={explorer} onRequestChange={vi.fn()} />
        </>,
      )
      const before = frame()
      fireEvent.load(before)
      const post = vi.spyOn(before.contentWindow!, 'postMessage')

      await user.click(screen.getByRole('button', { name: 'Switch to dark mode' }))
      expect(post.mock.calls).toEqual([message('dark')])
      await user.click(screen.getByRole('button', { name: 'Switch to light mode' }))
      expect(post.mock.calls).toEqual([message('dark'), message('light')])

      expect(frame()).toBe(before)
      expect(frame()).toHaveAttribute('src', `${explorer.src}?theme=light`)
    })
  })

  describe('a new build', () => {
    it('mounts a fresh frame, loading again', () => {
      const { rerender } = renderFrame()
      const before = frame()
      fireEvent.load(before)
      expect(screen.queryByText('Loading the explorer')).not.toBeInTheDocument()

      const rebuilt = makeExplorer({ version: 2, src: '/api/missions/m1/explorer/2/index.html' })
      rerender(<ExplorerFrame explorer={rebuilt} onRequestChange={vi.fn()} />)
      expect(frame()).not.toBe(before)
      expect(frame()).toHaveAttribute('src', '/api/missions/m1/explorer/2/index.html?theme=light')
      expect(screen.getByText('Loading the explorer')).toBeInTheDocument()
    })

    it('keeps the same frame when only the words around it change', () => {
      const { rerender } = renderFrame()
      const before = frame()
      rerender(<ExplorerFrame explorer={makeExplorer({ description: 'Reworded.' })} onRequestChange={vi.fn()} />)
      expect(frame()).toBe(before)
    })
  })

  describe('while loading', () => {
    it('covers the frame with a calm note until it has loaded', () => {
      renderFrame()
      expect(screen.getByRole('status')).toHaveTextContent('Loading the explorer')
      fireEvent.load(frame())
      expect(screen.queryByRole('status')).not.toBeInTheDocument()
    })

    it('after 20 seconds offers a way around, without claiming anything broke', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      const { onRequestChange } = renderFrame()
      act(() => vi.advanceTimersByTime(SLOW_MS - 1))
      expect(screen.queryByText(/longer than usual/)).not.toBeInTheDocument()

      act(() => vi.advanceTimersByTime(1))
      const note = screen.getByRole('status')
      expect(note).toHaveTextContent('This is taking longer than usual')
      expect(note.textContent).not.toMatch(/fail|error|broke|wrong/i)
      const link = screen.getByRole('link', { name: 'Open in new tab' })
      expect(link).toHaveAttribute('href', `${explorer.src}?theme=light`)
      expect(link).toHaveAttribute('target', '_blank')
      expect(link).toHaveAttribute('rel', 'noreferrer')

      await user.click(screen.getByRole('button', { name: 'request a change' }))
      expect(onRequestChange).toHaveBeenCalledTimes(1)
    })

    it('drops the note if the frame loads after all', () => {
      renderFrame()
      act(() => vi.advanceTimersByTime(SLOW_MS))
      fireEvent.load(frame())
      expect(screen.queryByRole('status')).not.toBeInTheDocument()
    })

    it('never shows the note for a frame that loaded in time', () => {
      renderFrame()
      fireEvent.load(frame())
      act(() => vi.advanceTimersByTime(SLOW_MS * 2))
      expect(screen.queryByText(/longer than usual/)).not.toBeInTheDocument()
    })

    it('leaves no timer behind when it goes away', () => {
      const { unmount } = renderFrame()
      unmount()
      expect(vi.getTimerCount()).toBe(0)
    })
  })
})
