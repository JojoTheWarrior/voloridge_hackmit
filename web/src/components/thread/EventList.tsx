import type { MissionEvent, Report } from '../../types'
import { ArtifactView } from '../artifacts/ArtifactView'
import { ConclusionCard } from './ConclusionCard'
import { ErrorEvent } from './ErrorEvent'
import { ReportCard } from './ReportCard'
import { StepEvent } from './StepEvent'
import { ThoughtEvent } from './ThoughtEvent'

function UserMessage({ text }: { text: string }) {
  return (
    <div className="flex justify-end">
      <p className="max-w-[80%] rounded-[18px] bg-fill px-4 py-2.5 text-[15px] leading-relaxed whitespace-pre-line">{text}</p>
    </div>
  )
}

interface EventProps extends Omit<EventListProps, 'events'> {
  event: MissionEvent
}

function Event({ event, live, missionId, report }: EventProps) {
  switch (event.kind) {
    case 'user_message':
      return <UserMessage text={event.text} />
    case 'thought':
      return <ThoughtEvent text={event.text} />
    case 'step':
      return <StepEvent label={event.label} state={event.state} live={live} />
    case 'artifact':
      return <ArtifactView artifact={event.artifact} />
    case 'conclusion':
      return <ConclusionCard verdict={event.verdict} summary={event.summary} stats={event.stats} />
    case 'error':
      return <ErrorEvent text={event.text} />
    case 'report':
      // The event only marks the place; without the report itself there is nothing to show.
      return missionId !== undefined && report ? <ReportCard missionId={missionId} report={report} /> : null
  }
}

interface EventListProps {
  events: MissionEvent[]
  /** Whether Devin is working right now; only then does the active step spin. */
  live: boolean
  /** Needed only by a list that may contain the `report` event. */
  missionId?: string
  report?: Report
}

/** Consecutive steps sit closer together than the rest of the thread so a run of them reads as one list. */
export function EventList({ events, live, missionId, report }: EventListProps) {
  if (events.length === 0) return null
  return (
    <div className="flex flex-col gap-6 [&>[data-step]+[data-step]]:-mt-3.5">
      {events.map((event) => (
        <Event key={event.id} event={event} live={live} missionId={missionId} report={report} />
      ))}
    </div>
  )
}
