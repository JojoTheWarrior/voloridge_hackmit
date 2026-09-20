import { Link, useParams } from 'react-router-dom'
import { MissionThread } from '../components/thread/MissionThread'
import { useMission } from '../hooks/useApiData'

function NotFound() {
  return (
    <div className="flex min-h-full flex-col items-center justify-center gap-2 px-6 pb-28 text-center">
      <h1 className="text-lg font-medium tracking-tight">Mission not found</h1>
      <p className="text-sm text-muted">It may have been removed, or the link is wrong.</p>
      <Link to="/" className="mt-3 rounded-full border border-line px-4 py-1.5 text-[13px] transition-colors duration-150 hover:border-faint">
        Start a new mission
      </Link>
    </div>
  )
}

export function MissionPage() {
  const { id = '' } = useParams()
  const { mission, loading, reconnecting } = useMission(id)

  // Rendering nothing while loading avoids flashing "not found" before the mission arrives.
  if (loading) return null
  if (!mission) return <NotFound />

  // Keyed so the fold, the draft reply and the scroll position never carry over to another mission.
  return <MissionThread key={mission.id} mission={mission} reconnecting={reconnecting} />
}
