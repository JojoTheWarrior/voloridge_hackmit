import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { Report } from '../../types'
import { reportPath } from '../report/paths'

interface ReportCardProps {
  missionId: string
  report: Report
}

/** Marks where in the thread the report arrived. The link is stretched over the card, so all of it opens the report. */
export function ReportCard({ missionId, report }: ReportCardProps) {
  return (
    <section
      aria-label="Report"
      className="fade-in group relative rounded-xl border border-line p-5 transition-colors duration-150 hover:border-faint"
    >
      <p className="text-xs text-muted">Report ready</p>
      <p className="mt-2 text-[17px] leading-snug font-medium tracking-tight text-balance">{report.headline}</p>
      <p className="mt-1.5 line-clamp-2 text-[13px] leading-relaxed text-muted">{report.summary}</p>
      <Link to={reportPath(missionId)} className="mt-4 inline-flex items-center gap-1 text-[13px] font-medium after:absolute after:inset-0 after:rounded-xl">
        View report
        <ArrowRight size={14} strokeWidth={1.75} aria-hidden="true" className="transition-transform duration-150 group-hover:translate-x-0.5" />
      </Link>
    </section>
  )
}
