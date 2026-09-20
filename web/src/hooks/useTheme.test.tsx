import { act, renderHook } from '@testing-library/react'
import { THEME_KEY, useTheme } from './useTheme'

let systemDark = false
let listeners: ((event: { matches: boolean }) => void)[] = []

function setSystemDark(value: boolean) {
  systemDark = value
  listeners.forEach((listener) => listener({ matches: value }))
}

beforeEach(() => {
  systemDark = false
  listeners = []
  localStorage.clear()
  delete document.documentElement.dataset.theme
  vi.stubGlobal('matchMedia', (query: string) => ({
    matches: query.includes('dark') && systemDark,
    addEventListener: (_: string, listener: (event: { matches: boolean }) => void) => listeners.push(listener),
    removeEventListener: (_: string, listener: (event: { matches: boolean }) => void) => {
      listeners = listeners.filter((l) => l !== listener)
    },
  }))
})
afterEach(() => vi.unstubAllGlobals())

const applied = () => document.documentElement.dataset.theme

describe('useTheme', () => {
  it('follows the system when nothing is stored', () => {
    systemDark = true
    const { result } = renderHook(() => useTheme())
    expect(result.current.theme).toBe('dark')
    expect(applied()).toBe('dark')
  })

  it('tracks the system changing while the app is open', () => {
    const { result } = renderHook(() => useTheme())
    expect(result.current.theme).toBe('light')
    act(() => setSystemDark(true))
    expect(result.current.theme).toBe('dark')
    expect(applied()).toBe('dark')
  })

  it('remembers an explicit choice and stops following the system', () => {
    const { result } = renderHook(() => useTheme())
    act(() => result.current.toggle())
    expect(result.current.theme).toBe('dark')
    expect(localStorage.getItem(THEME_KEY)).toBe('dark')
    act(() => setSystemDark(false))
    expect(result.current.theme).toBe('dark')
    act(() => result.current.toggle())
    expect(localStorage.getItem(THEME_KEY)).toBe('light')
    expect(applied()).toBe('light')
  })

  it('restores a stored choice over the system setting', () => {
    systemDark = true
    localStorage.setItem(THEME_KEY, 'light')
    expect(renderHook(() => useTheme()).result.current.theme).toBe('light')
  })

  it('ignores a stored value it does not understand', () => {
    localStorage.setItem(THEME_KEY, 'sepia')
    expect(renderHook(() => useTheme()).result.current.theme).toBe('light')
  })

  it('works when storage is blocked', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('denied')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('denied')
    })
    const { result } = renderHook(() => useTheme())
    act(() => result.current.toggle())
    expect(result.current.theme).toBe('dark')
    expect(applied()).toBe('dark')
    vi.restoreAllMocks()
  })

  it('works where matchMedia does not exist', () => {
    vi.stubGlobal('matchMedia', undefined)
    expect(renderHook(() => useTheme()).result.current.theme).toBe('light')
  })

  it('stops listening to the system when unmounted', () => {
    const { unmount } = renderHook(() => useTheme())
    expect(listeners).toHaveLength(1)
    unmount()
    expect(listeners).toHaveLength(0)
  })
})
