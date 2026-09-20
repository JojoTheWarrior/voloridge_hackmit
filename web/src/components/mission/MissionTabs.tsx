import { LoaderCircle } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import type { Mission } from '../../types'
import { explorerPath, missionPath, reportPath } from './paths'

type Progress = 'pending' | 'ready' | undefined

function Marker({ progress }: { progress: Progress }) {
  if (!progress) return null
  return (
    <>
      {progress === 'pending' ? (
        <LoaderCircle size={11} strokeWidth={2} aria-hidden="true" className="animate-spin" />
      ) : (
        <span data-marker="ready" aria-hidden="true" className="h-1 w-1 rounded-full bg-current" />
      )}
      <span className="sr-only">{progress === 'pending' ? ', in progress' : ', ready'}</span>
    </>
  )
}

const tabClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-1.5 rounded-full px-3 py-1 text-[13px] transition-colors duration-150 ${
    isActive ? 'bg-fill text-ink' : 'text-muted hover:text-ink'
  }`

const progressOf = (pending: boolean, content: unknown): Progress => (pending ? 'pending' : content ? 'ready' : undefined)

/** The three views of a mission. A marker says what is waiting behind a tab before it is opened. */
export function MissionTabs({ mission, className = '' }: { mission: Mission; className?: string }) {
  return (
    <nav aria-label="Mission views" className={`flex items-center gap-0.5 ${className}`}>
      <NavLink to={missionPath(mission.id)} end className={tabClass}>
        Thread
      </NavLink>
      <NavLink to={reportPath(mission.id)} className={tabClass}>
        Report
        <Marker progress={progressOf(mission.reportPending, mission.report)} />
      </NavLink>
      <NavLink to={explorerPath(mission.id)} className={tabClass}>
        Explorer
        <Marker progress={progressOf(mission.explorerPending, mission.explorer)} />
      </NavLink>
    </nav>
  )
}
