import { Database, Plus } from 'lucide-react'
import { useId } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { useMissions } from '../hooks/useApiData'
import type { MissionSummary } from '../types'
import { CastleLogo } from './CastleLogo'
import { StatusDot } from './StatusDot'

const rowClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-[13px] transition-colors duration-150 ${
    isActive ? 'bg-hover text-ink' : 'hover:bg-fill'
  }`

function MissionGroup({ label, missions, onNavigate }: { label: string; missions: MissionSummary[]; onNavigate?: () => void }) {
  const labelId = useId()
  if (missions.length === 0) return null
  return (
    <div role="group" aria-labelledby={labelId} className="mt-5">
      <div id={labelId} className="px-2.5 pb-1 text-xs text-muted">
        {label}
      </div>
      {missions.map((mission) => (
        <NavLink
          key={mission.id}
          to={`/missions/${mission.id}`}
          onClick={onNavigate}
          className={(state) => `${rowClass(state)} ${mission.status !== 'done' || state.isActive ? 'text-ink' : 'text-muted'}`}
        >
          <StatusDot status={mission.status} />
          <span className="truncate">{mission.title}</span>
        </NavLink>
      ))}
    </div>
  )
}

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const missions = useMissions() ?? []

  return (
    <nav aria-label="Main" className="flex h-full w-60 flex-col border-r border-line-soft bg-side p-3">
      <Link
        to="/"
        aria-label="kingdom"
        onClick={onNavigate}
        className="flex items-center gap-2 px-2.5 pt-1.5 pb-4 text-[15px] font-medium tracking-tight"
      >
        <CastleLogo />
        <span aria-hidden="true">kingdom</span>
      </Link>

      <Link
        to="/"
        onClick={onNavigate}
        className="flex items-center justify-center gap-1.5 rounded-lg border border-line bg-paper px-2.5 py-1.5 text-[13px] transition-colors duration-150 hover:border-faint"
      >
        <Plus size={14} strokeWidth={1.75} aria-hidden="true" />
        New mission
      </Link>

      <div className="-mx-1 min-h-0 flex-1 overflow-y-auto px-1">
        <MissionGroup label="Active" missions={missions.filter((m) => m.status !== 'done')} onNavigate={onNavigate} />
        <MissionGroup label="Done" missions={missions.filter((m) => m.status === 'done')} onNavigate={onNavigate} />
      </div>

      <div className="border-t border-line-soft pt-2">
        <NavLink to="/datasets" onClick={onNavigate} className={rowClass}>
          <Database size={14} strokeWidth={1.75} aria-hidden="true" />
          Datasets
        </NavLink>
      </div>
    </nav>
  )
}
