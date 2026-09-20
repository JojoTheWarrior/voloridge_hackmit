import { LoaderCircle } from 'lucide-react'
import type { ReactNode } from 'react'

interface CenteredStateProps {
  title: string
  /** The page's own heading is level 1; inside a mission the header already holds that. */
  level?: 1 | 2
  /** Devin is at work on what this view will show. */
  busy?: boolean
  children: ReactNode
}

/** A view with nothing to show yet: a heading and a few quiet lines, set slightly above the middle. */
export function CenteredState({ title, level = 2, busy = false, children }: CenteredStateProps) {
  const Heading = level === 1 ? 'h1' : 'h2'
  return (
    <div role={busy ? 'status' : undefined} className="fade-in flex min-h-full flex-col items-center justify-center gap-2 px-6 pt-10 pb-28 text-center">
      {busy && <LoaderCircle size={16} strokeWidth={1.75} aria-hidden="true" className="mb-2 animate-spin text-muted" />}
      <Heading className="text-lg font-medium tracking-tight">{title}</Heading>
      {children}
    </div>
  )
}
