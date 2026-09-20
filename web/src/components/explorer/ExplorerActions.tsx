import { ArrowUpRight, LoaderCircle } from 'lucide-react'
import { useTheme } from '../../hooks/useTheme'
import type { Explorer } from '../../types'
import { OUTLINE_PILL, RESTING_PILL } from '../mission/pill'
import { themedSrc } from './src'

interface ExplorerActionsProps {
  explorer: Explorer
  /** Devin is building the next version; this one stays usable meanwhile. */
  busy: boolean
  onRequestChange: () => void
}

/** On phones a label is one word, so the explorer's title keeps some room. */
function Label({ short, full }: { short: string; full: string }) {
  return (
    <>
      <span className="sm:hidden">{short}</span>
      <span className="max-sm:hidden">{full}</span>
    </>
  )
}

export function ExplorerActions({ explorer, busy, onRequestChange }: ExplorerActionsProps) {
  const { theme } = useTheme()

  return (
    <div className="flex h-12 shrink-0 items-center gap-3 px-4 text-[13px] sm:px-6">
      <div className="flex min-w-0 flex-1 items-baseline gap-2.5">
        <h2 className="truncate font-medium">{explorer.title}</h2>
        <p className="min-w-0 flex-1 truncate text-muted max-lg:hidden" title={explorer.description}>
          {explorer.description}
        </p>
      </div>
      {busy && (
        <p role="status" className="flex shrink-0 items-center gap-1.5 text-muted">
          <LoaderCircle size={13} strokeWidth={1.75} aria-hidden="true" className="animate-spin" />
          <span className="max-md:sr-only">Devin is updating this</span>
        </p>
      )}
      <a href={themedSrc(explorer, theme)} target="_blank" rel="noreferrer" aria-label="Open in new tab" className={OUTLINE_PILL}>
        <Label short="Open" full="Open in new tab" />
        <ArrowUpRight size={14} strokeWidth={1.75} aria-hidden="true" className="-mr-0.5" />
      </a>
      <button
        type="button"
        aria-label="Request a change"
        aria-disabled={busy}
        onClick={busy ? undefined : onRequestChange}
        className={busy ? RESTING_PILL : OUTLINE_PILL}
      >
        <Label short="Change" full="Request a change" />
      </button>
    </div>
  )
}
