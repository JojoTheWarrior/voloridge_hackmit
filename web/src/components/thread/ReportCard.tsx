import type { Report } from '../../types'
import { reportPath } from '../mission/paths'
import { DeliveryCard } from './DeliveryCard'

export function ReportCard({ missionId, report }: { missionId: string; report: Report }) {
  return <DeliveryCard label="Report" eyebrow="Report ready" title={report.headline} summary={report.summary} to={reportPath(missionId)} action="View report" />
}
