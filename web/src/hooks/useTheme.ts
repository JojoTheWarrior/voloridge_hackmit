import { useSyncExternalStore } from 'react'
import { currentTheme, subscribeTheme, toggleTheme, type Theme } from './themeStore'

export { THEME_KEY, type Theme } from './themeStore'

/** One theme for the whole app: the toggle, and anything that has to tell a frame which side it is on. */
export function useTheme(): { theme: Theme; toggle: () => void } {
  return { theme: useSyncExternalStore(subscribeTheme, currentTheme), toggle: toggleTheme }
}
