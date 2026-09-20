import { useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'

/** Also read by the inline script in index.html, which applies the theme before first paint. */
export const THEME_KEY = 'kingdom.theme'

const DARK_QUERY = '(prefers-color-scheme: dark)'

function storedChoice(): Theme | null {
  try {
    const value = localStorage.getItem(THEME_KEY)
    return value === 'light' || value === 'dark' ? value : null
  } catch {
    return null
  }
}

const systemQuery = () => (typeof window.matchMedia === 'function' ? window.matchMedia(DARK_QUERY) : null)

/** Follows the system until the user picks a side; after that their choice sticks. */
export function useTheme(): { theme: Theme; toggle: () => void } {
  const [choice, setChoice] = useState<Theme | null>(storedChoice)
  const [systemDark, setSystemDark] = useState(() => systemQuery()?.matches ?? false)
  const theme = choice ?? (systemDark ? 'dark' : 'light')

  useEffect(() => {
    const query = systemQuery()
    if (!query) return
    const onChange = (event: { matches: boolean }) => setSystemDark(event.matches)
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [])

  useEffect(() => {
    document.documentElement.dataset.theme = theme
  }, [theme])

  function toggle() {
    const next = theme === 'dark' ? 'light' : 'dark'
    setChoice(next)
    try {
      localStorage.setItem(THEME_KEY, next)
    } catch {
      // Storage is blocked; the choice still holds for this visit.
    }
  }

  return { theme, toggle }
}
