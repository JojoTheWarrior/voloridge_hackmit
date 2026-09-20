import { useState } from 'react'
import { ChangeDialog } from '../components/explorer/ChangeDialog'
import { ExplorerActions } from '../components/explorer/ExplorerActions'
import { ExplorerFrame } from '../components/explorer/ExplorerFrame'
import { ExplorerInvitation } from '../components/explorer/ExplorerInvitation'
import { CenteredState } from '../components/mission/CenteredState'
import { useBuildExplorer } from '../hooks/useBuildExplorer'
import { useOutletMission } from '../hooks/useOutletMission'

export function ExplorerPage() {
  const mission = useOutletMission()
  const { busy, build } = useBuildExplorer(mission)
  const [changing, setChanging] = useState(false)

  if (mission.explorer) {
    return (
      <div className="flex h-full flex-col">
        <ExplorerActions explorer={mission.explorer} busy={busy} onRequestChange={() => setChanging(true)} />
        <ExplorerFrame explorer={mission.explorer} onRequestChange={() => setChanging(true)} />
        {changing && <ChangeDialog onSubmit={build} onClose={() => setChanging(false)} />}
      </div>
    )
  }
  if (mission.explorerPending) {
    return (
      <CenteredState title="Devin is building the explorer" busy>
        <p className="max-w-sm text-sm leading-relaxed text-muted">This can take several minutes. You can keep using the thread meanwhile.</p>
      </CenteredState>
    )
  }
  return <ExplorerInvitation concluded={mission.events.some((e) => e.kind === 'conclusion')} busy={busy} onBuild={build} />
}
