import { ArrowUpRight } from 'lucide-react'
import { useRef } from 'react'
import { useApi } from '../../api/context'
import type { Mission, MissionStatus } from '../../types'
import { StatusDot } from '../StatusDot'

const STATUS_TEXT: Record<MissionStatus, string> = {
  working: 'Devin is working',
  waiting: 'Waiting for you',
  done: 'Done',
  failed: 'Failed',
}

interface MissionHeaderProps {
  mission: Mission
  /** True while reads are failing and the thread below may be out of date. */
  reconnecting: boolean
}

export function MissionHeader({ mission, reconnecting }: MissionHeaderProps) {
  const api = useApi()
  const marking = useRef(false)

  async function markDone() {
    if (marking.current) return
    marking.current = true
    try {
      await api.markDone(mission.id)
    } catch {
      // Nothing changed; the button is still there to try again.
    } finally {
      marking.current = false
    }
  }

  return (
    <header className="flex h-12 shrink-0 items-center gap-2.5 border-b border-line-soft bg-white px-6 text-[13px]">
      <StatusDot status={mission.status} />
      <h1 className="truncate font-medium">{mission.title}</h1>
      <span className="shrink-0 text-muted">{reconnecting ? 'Reconnecting' : STATUS_TEXT[mission.status]}</span>
      <div className="ml-auto flex shrink-0 items-center gap-4 pl-3">
        {mission.sessionUrl && (
          <a
            href={mission.sessionUrl}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-0.5 text-muted transition-colors duration-150 hover:text-ink"
          >
            Open in Devin
            <ArrowUpRight size={14} strokeWidth={1.75} aria-hidden="true" />
          </a>
        )}
        {mission.status !== 'done' && (
          <button
            type="button"
            onClick={markDone}
            className="rounded-full border border-line px-3 py-1 transition-colors duration-150 hover:border-faint"
          >
            Mark done
          </button>
        )}
      </div>
    </header>
  )
}
