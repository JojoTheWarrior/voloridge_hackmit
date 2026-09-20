import type { MissionEvent } from '../../types'
import { ArtifactView } from '../artifacts/ArtifactView'
import { ConclusionCard } from './ConclusionCard'
import { ErrorEvent } from './ErrorEvent'
import { StepEvent } from './StepEvent'
import { ThoughtEvent } from './ThoughtEvent'

function UserMessage({ text }: { text: string }) {
  return (
    <div className="flex justify-end">
      <p className="max-w-[80%] rounded-[18px] bg-fill px-4 py-2.5 text-[15px] leading-relaxed whitespace-pre-line">{text}</p>
    </div>
  )
}

function Event({ event, live }: { event: MissionEvent; live: boolean }) {
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
  }
}

interface EventListProps {
  events: MissionEvent[]
  /** Whether Devin is working right now; only then does the active step spin. */
  live: boolean
}

/** Consecutive steps sit closer together than the rest of the thread so a run of them reads as one list. */
export function EventList({ events, live }: EventListProps) {
  if (events.length === 0) return null
  return (
    <div className="flex flex-col gap-6 [&>[data-step]+[data-step]]:-mt-3.5">
      {events.map((event) => (
        <Event key={event.id} event={event} live={live} />
      ))}
    </div>
  )
}
