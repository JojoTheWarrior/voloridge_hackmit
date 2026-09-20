import { LoaderCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { OUTLINE_PILL, RESTING_PILL } from '../mission/pill'

const COPIED_MS = 2000

function CopyLink() {
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!copied) return
    const timer = setTimeout(() => setCopied(false), COPIED_MS)
    return () => clearTimeout(timer)
  }, [copied])

  async function copy() {
    try {
      await navigator.clipboard.writeText(window.location.href)
      setCopied(true)
    } catch {
      // No clipboard here; the address bar still has the link.
    }
  }

  return (
    <button type="button" onClick={copy} className="rounded-full px-3 py-1 text-[13px] text-muted transition-colors duration-150 hover:text-ink">
      {copied ? 'Copied' : 'Copy link'}
    </button>
  )
}

interface ReportActionsProps {
  /** Devin is rewriting the report; the one on the page stays until the new one lands. */
  busy: boolean
  onRegenerate: () => void
}

export function ReportActions({ busy, onRegenerate }: ReportActionsProps) {
  return (
    <div role="group" aria-label="Report actions" className="flex items-center gap-1.5 print:hidden">
      <CopyLink />
      {busy ? (
        <button type="button" aria-busy="true" aria-disabled="true" className={RESTING_PILL}>
          <LoaderCircle size={13} strokeWidth={1.75} aria-hidden="true" className="animate-spin" />
          Rewriting
        </button>
      ) : (
        <button type="button" onClick={onRegenerate} className={OUTLINE_PILL}>
          Regenerate
        </button>
      )}
      <button
        type="button"
        onClick={() => window.print()}
        className="shrink-0 rounded-full bg-ink px-3.5 py-1 text-[13px] text-paper transition-colors duration-150 hover:bg-ink/85"
      >
        Export PDF
      </button>
    </div>
  )
}
