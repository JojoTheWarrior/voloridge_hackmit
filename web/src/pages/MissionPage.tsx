import { Link, useParams } from 'react-router-dom'
import { ResultCard } from '../components/ResultCard'
import { StepList } from '../components/StepList'
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
  const { mission, loading } = useMission(id)

  // Rendering nothing while loading avoids flashing "not found" before the mission arrives.
  if (loading) return null
  if (!mission) return <NotFound />

  return (
    <article className="mx-auto flex w-full max-w-[720px] flex-col gap-7 px-6 pt-12 pb-24">
      <div className="flex justify-end">
        <p className="max-w-[80%] rounded-[18px] bg-fill px-4 py-2.5 text-[15px] leading-relaxed">{mission.hypothesis}</p>
      </div>

      <StepList steps={mission.steps} status={mission.status} elapsedSeconds={mission.elapsedSeconds} />

      {mission.result && <ResultCard result={mission.result} />}

      {mission.status === 'failed' && (
        <div role="alert" className="rounded-xl border border-line p-5">
          <p className="text-[15px] font-medium">This mission failed</p>
          <p className="mt-1 text-[15px] leading-relaxed text-muted">{mission.error}</p>
        </div>
      )}
    </article>
  )
}
