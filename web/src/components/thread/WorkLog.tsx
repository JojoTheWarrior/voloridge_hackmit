import { ChevronRight } from 'lucide-react'
import { useState } from 'react'
import type { MissionEvent } from '../../types'
import { EventList } from './EventList'

/** The thoughts, steps and artifacts behind a finished mission, folded behind one line. */
export function WorkLog({ events }: { events: MissionEvent[] }) {
  const [expanded, setExpanded] = useState(false)
  if (events.length === 0) return null

  return (
    <div>
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-[13px] text-muted transition-colors duration-150 hover:text-ink"
      >
        Show the work
        <ChevronRight
          size={14}
          strokeWidth={1.75}
          aria-hidden="true"
          className={`transition-transform duration-150 ${expanded ? 'rotate-90' : ''}`}
        />
      </button>
      {expanded && (
        <div className="fade-in mt-4 border-l border-line-soft pl-4">
          <EventList events={events} live={false} />
        </div>
      )}
    </div>
  )
}
