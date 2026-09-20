import { CenteredState } from '../components/mission/CenteredState'
import { OUTLINE_PILL } from '../components/mission/pill'
import { canReport } from '../components/report/canReport'
import { ReportActions } from '../components/report/ReportActions'
import { ReportDocument } from '../components/report/ReportDocument'
import { useGenerateReport } from '../hooks/useGenerateReport'
import { useOutletMission } from '../hooks/useOutletMission'

const QUIET_LINE = 'max-w-sm text-sm leading-relaxed text-muted'

export function ReportPage() {
  const mission = useOutletMission()
  const { busy, generate } = useGenerateReport(mission)

  if (mission.report) {
    return (
      <div className="h-full overflow-y-auto print:h-auto print:overflow-visible">
        <ReportDocument mission={mission} report={mission.report} actions={<ReportActions busy={busy} onRegenerate={generate} />} />
      </div>
    )
  }
  if (busy) {
    return (
      <CenteredState title="Devin is writing the report" busy>
        <p className={QUIET_LINE}>This can take a few minutes. You can keep using the thread meanwhile.</p>
      </CenteredState>
    )
  }
  if (!canReport(mission)) {
    return (
      <CenteredState title="Nothing to report on yet">
        <p className={QUIET_LINE}>A report looks back over what Devin found. Come back once the thread has some findings in it.</p>
      </CenteredState>
    )
  }
  return (
    <CenteredState title="Write up the mission">
      <p className={QUIET_LINE}>Devin looks back over the thread and writes a short paper: the finding, the figures behind it, the caveats and what to ask next.</p>
      <button type="button" onClick={generate} className={`${OUTLINE_PILL} mt-3 px-4 py-1.5`}>
        Generate report
      </button>
    </CenteredState>
  )
}
