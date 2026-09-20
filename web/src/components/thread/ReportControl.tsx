import { LoaderCircle } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useGenerateReport } from '../../hooks/useGenerateReport'
import type { Mission } from '../../types'
import { reportPath } from '../report/paths'
import { OUTLINE_PILL } from '../report/pill'

const DEVIN_KINDS = new Set(['thought', 'step', 'artifact', 'conclusion'])

/** A report needs something from Devin to look back on, and a failed mission only has that if it concluded first. */
function canReport({ status, events }: Pick<Mission, 'status' | 'events'>): boolean {
  if (status === 'failed') return events.some((e) => e.kind === 'conclusion')
  return events.some((e) => DEVIN_KINDS.has(e.kind))
}

function Spinner() {
  return <LoaderCircle size={13} strokeWidth={1.75} aria-hidden="true" className="animate-spin text-muted" />
}

/** On phones every state is just "Report", so the title keeps the room. */
function Label({ full }: { full: string }) {
  return (
    <>
      <span className="sm:hidden">Report</span>
      <span className="max-sm:hidden">{full}</span>
    </>
  )
}

export function ReportControl({ mission }: { mission: Mission }) {
  const { busy, generate } = useGenerateReport(mission)

  if (mission.report) {
    return (
      <Link to={reportPath(mission.id)} aria-label="View report" aria-busy={busy} className={OUTLINE_PILL}>
        {busy && <Spinner />}
        <Label full="View report" />
      </Link>
    )
  }
  if (!canReport(mission)) return null
  if (busy) {
    return (
      <button type="button" aria-label="Writing report" aria-busy="true" aria-disabled="true" className={`${OUTLINE_PILL} cursor-default text-muted hover:border-line`}>
        <Spinner />
        <Label full="Writing report" />
      </button>
    )
  }
  return (
    <button type="button" aria-label="Generate report" onClick={generate} className={OUTLINE_PILL}>
      <Label full="Generate report" />
    </button>
  )
}
