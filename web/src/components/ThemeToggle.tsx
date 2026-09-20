import { Moon, Sun } from 'lucide-react'
import { useTheme } from '../hooks/useTheme'

export function ThemeToggle() {
  const { theme, toggle } = useTheme()
  const Icon = theme === 'dark' ? Sun : Moon
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
      className="rounded-md p-1.5 text-muted transition-colors duration-150 hover:bg-fill hover:text-ink"
    >
      <Icon size={14} strokeWidth={1.75} aria-hidden="true" />
    </button>
  )
}
