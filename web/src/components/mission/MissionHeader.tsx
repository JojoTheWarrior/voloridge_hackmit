import { ArrowUpRight } from 'lucide-react'
import { useRef } from 'react'
import { useApi } from '../../api/context'
import type { Mission, MissionStatus } from '../../types'
import { StatusDot } from '../StatusDot'
import { MissionTabs } from './MissionTabs'
import { OUTLINE_PILL } from './pill'

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
    // One row from tablet up; on phones the tabs take a second row so the title keeps the first.
    <header className="grid shrink-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 border-b border-line-soft bg-paper px-4 text-[13px] sm:grid-cols-[minmax(0,1fr)_auto_auto] sm:gap-x-5 sm:px-6 xl:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] print:hidden">
      <div className="flex h-12 min-w-0 items-center gap-2.5">
        <StatusDot status={mission.status} />
        <h1 className="truncate font-medium">{mission.title}</h1>
        {/* On phones the dot carries the status so the title keeps the room; an outage is always spelled out. */}
        <span className={`shrink-0 text-muted ${reconnecting ? '' : 'max-sm:hidden'}`}>
          {reconnecting ? 'Reconnecting' : STATUS_TEXT[mission.status]}
        </span>
      </div>
      <MissionTabs mission={mission} className="max-sm:order-last max-sm:col-span-2 max-sm:-mx-1.5 max-sm:pb-2" />
      <div className="flex shrink-0 items-center justify-end gap-3 sm:gap-4">
        {mission.sessionUrl && (
          <a
            href={mission.sessionUrl}
            target="_blank"
            rel="noreferrer"
            aria-label="Open in Devin"
            className="flex items-center gap-0.5 text-muted transition-colors duration-150 hover:text-ink"
          >
            <span className="max-sm:hidden">Open in&nbsp;</span>Devin
            <ArrowUpRight size={14} strokeWidth={1.75} aria-hidden="true" />
          </a>
        )}
        {mission.status !== 'done' && (
          <button type="button" onClick={markDone} className={OUTLINE_PILL}>
            Mark done
          </button>
        )}
      </div>
    </header>
  )
}
