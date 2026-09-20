import { Outlet, useParams } from 'react-router-dom'
import { MissionHeader } from '../components/mission/MissionHeader'
import { MissionNotFound } from '../components/mission/MissionNotFound'
import { useMission } from '../hooks/useApiData'

/** Loads the mission once for its three views, which share the header and its tabs. */
export function MissionLayout() {
  const { id = '' } = useParams()
  const { mission, loading, reconnecting } = useMission(id)

  // Rendering nothing while loading avoids flashing "not found" before the mission arrives.
  if (loading) return null
  if (!mission) return <MissionNotFound />

  return (
    <div className="flex h-full flex-col print:block print:h-auto">
      <MissionHeader mission={mission} reconnecting={reconnecting} />
      {/* Keyed so a draft, a fold or a scroll position never carries over to another mission. */}
      <div key={mission.id} className="min-h-0 flex-1">
        <Outlet context={mission} />
      </div>
    </div>
  )
}
