import type { Theme } from '../../hooks/useTheme'
import type { Explorer } from '../../types'

/** The explorer's address, telling it which theme to start in. */
export function themedSrc({ src }: Pick<Explorer, 'src'>, theme: Theme): string {
  return `${src}?theme=${theme}`
}
