export type Theme = 'light' | 'dark'

/** Also read by the inline script in index.html, which applies the theme before first paint. */
export const THEME_KEY = 'kingdom.theme'

const DARK_QUERY = '(prefers-color-scheme: dark)'

const listeners = new Set<() => void>()
let choice: Theme | null = null
let systemDark = false
let query: MediaQueryList | null = null

function storedChoice(): Theme | null {
  try {
    const value = localStorage.getItem(THEME_KEY)
    return value === 'light' || value === 'dark' ? value : null
  } catch {
    return null
  }
}

function readEnvironment() {
  choice = storedChoice()
  query = typeof window.matchMedia === 'function' ? window.matchMedia(DARK_QUERY) : null
  systemDark = query?.matches ?? false
}

/** Follows the system until the user picks a side; after that their choice sticks. */
export function currentTheme(): Theme {
  // With nobody subscribed nothing keeps the state fresh, and a first render must not start from a stale answer.
  if (listeners.size === 0) readEnvironment()
  return choice ?? (systemDark ? 'dark' : 'light')
}

function publish() {
  document.documentElement.dataset.theme = currentTheme()
  listeners.forEach((listener) => listener())
}

function onSystemChange(event: { matches: boolean }) {
  systemDark = event.matches
  publish()
}

export function subscribeTheme(listener: () => void): () => void {
  if (listeners.size === 0) {
    document.documentElement.dataset.theme = currentTheme()
    query?.addEventListener('change', onSystemChange)
  }
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
    if (listeners.size === 0) query?.removeEventListener('change', onSystemChange)
  }
}

export function toggleTheme() {
  choice = currentTheme() === 'dark' ? 'light' : 'dark'
  try {
    localStorage.setItem(THEME_KEY, choice)
  } catch {
    // Storage is blocked; the choice still holds for this visit.
  }
  publish()
}
