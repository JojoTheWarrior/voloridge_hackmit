import { Database, LoaderCircle, Pencil, Pin, PinOff, Plus, Trash2 } from 'lucide-react'
import { useId, useState } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useApi } from '../api/context'
import { useMissions } from '../hooks/useApiData'
import type { MissionSummary } from '../types'
import { CastleLogo } from './CastleLogo'
import { MissionActionDialog } from './MissionActionDialog'
import { StatusDot } from './StatusDot'

const rowClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-[13px] transition-colors duration-150 ${
    isActive ? 'bg-hover text-ink' : 'hover:bg-fill'
  }`

function MissionGroup({ label, missions, onNavigate, onAction, onPin, pinning }: {
  label: string
  missions: MissionSummary[]
  onNavigate?: () => void
  onAction: (mission: MissionSummary, action: 'rename' | 'delete') => void
  onPin: (mission: MissionSummary) => void
  pinning?: string
}) {
  const labelId = useId()
  if (missions.length === 0) return null
  return (
    <div role="group" aria-labelledby={labelId} className="mt-5">
      <div id={labelId} className="px-2.5 pb-1 text-xs text-muted">
        {label}
      </div>
      {missions.map((mission) => (
        <div key={mission.id} className="mission-sidebar-row relative">
        <NavLink
          to={`/missions/${mission.id}`}
          title={mission.title}
          onClick={onNavigate}
          className={(state) => `${rowClass(state)} ${mission.status !== 'done' || state.isActive ? 'text-ink' : 'text-muted'}`}
        >
          <StatusDot status={mission.status} />
          <span className="truncate">{mission.title}</span>
        </NavLink>
        <div className="mission-sidebar-actions absolute top-0.5 right-0 flex items-center rounded-md bg-side p-0.5 shadow-[-8px_0_8px_var(--color-side)]">
          <button type="button" onClick={() => onPin(mission)} disabled={pinning === mission.id}
            aria-label={`${mission.pinned ? 'Unpin' : 'Pin'} ${mission.title}`} title={mission.pinned ? 'Unpin mission' : 'Pin mission'}
            className="rounded p-1.5 text-muted hover:bg-hover hover:text-ink disabled:opacity-40">
            {pinning === mission.id ? <LoaderCircle size={13} className="animate-spin" /> : mission.pinned ? <PinOff size={13} /> : <Pin size={13} />}
          </button>
          <button type="button" onClick={() => onAction(mission, 'rename')} aria-label={`Rename ${mission.title}`} title="Rename mission"
            className="rounded p-1.5 text-muted hover:bg-hover hover:text-ink"><Pencil size={13} /></button>
          <button type="button" onClick={() => onAction(mission, 'delete')} aria-label={`Delete ${mission.title}`} title="Delete mission"
            className="rounded p-1.5 text-muted hover:bg-hover hover:text-ink"><Trash2 size={13} /></button>
        </div>
        </div>
      ))}
    </div>
  )
}

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const api = useApi()
  const location = useLocation()
  const navigate = useNavigate()
  const missions = useMissions() ?? []
  const [pinnedOnly, setPinnedOnly] = useState(() => {
    try { return localStorage.getItem('kingdom.missions.pinnedOnly') === 'true' } catch { return false }
  })
  const [editing, setEditing] = useState<{ mission: MissionSummary; action: 'rename' | 'delete' }>()
  const [pinning, setPinning] = useState<string>()
  const [error, setError] = useState('')

  async function togglePin(mission: MissionSummary) {
    setPinning(mission.id)
    setError('')
    try { await api.updateMission(mission.id, { pinned: !mission.pinned }) }
    catch { setError('Could not update pins. Please try again.') }
    finally { setPinning(undefined) }
  }

  const groupProps = { onNavigate, onPin: togglePin, pinning, onAction: (mission: MissionSummary, action: 'rename' | 'delete') => setEditing({ mission, action }) }

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
        <div className="mt-5 flex items-center gap-1 px-2.5" aria-label="Mission filter">
          {([false, true] as const).map((value) => <button key={String(value)} type="button" aria-pressed={pinnedOnly === value}
            onClick={() => {
              setPinnedOnly(value)
              try { localStorage.setItem('kingdom.missions.pinnedOnly', String(value)) } catch { /* Storage can be unavailable in private browsers. */ }
            }}
            className={`rounded px-2 py-1 text-xs transition-colors ${pinnedOnly === value ? 'bg-hover text-ink' : 'text-muted hover:text-ink'}`}>
            {value ? 'Pinned only' : 'All missions'}
          </button>)}
        </div>
        {error && <p role="alert" className="px-2.5 pt-3 text-xs text-muted">{error}</p>}
        <MissionGroup label="Pinned" missions={missions.filter((m) => m.pinned)} {...groupProps} />
        {pinnedOnly && !missions.some((m) => m.pinned) && <p className="px-2.5 py-5 text-xs leading-relaxed text-muted">Pin your best missions to keep them here. Switch to All missions to choose them.</p>}
        {!pinnedOnly && <>
          <MissionGroup label="Active" missions={missions.filter((m) => !m.pinned && m.status !== 'done')} {...groupProps} />
          <MissionGroup label="Done" missions={missions.filter((m) => !m.pinned && m.status === 'done')} {...groupProps} />
        </>}
      </div>

      <div className="border-t border-line-soft pt-2">
        <NavLink to="/datasets" onClick={onNavigate} className={rowClass}>
          <Database size={14} strokeWidth={1.75} aria-hidden="true" />
          Datasets
        </NavLink>
      </div>
      {editing && <MissionActionDialog mission={editing.mission} action={editing.action} onClose={() => setEditing(undefined)}
        onSubmit={async (title) => {
          if (editing.action === 'rename') await api.updateMission(editing.mission.id, { title })
          else {
            await api.deleteMission(editing.mission.id)
            const path = `/missions/${editing.mission.id}`
            if (location.pathname === path || location.pathname.startsWith(`${path}/`)) {
              navigate('/')
              onNavigate?.()
            }
          }
        }} />}
    </nav>
  )
}
