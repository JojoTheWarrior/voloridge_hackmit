import { MissionThread } from '../components/thread/MissionThread'
import { useOutletMission } from '../hooks/useOutletMission'
import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

export function MissionPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const [draft] = useState(() => typeof location.state?.replyDraft === 'string' ? location.state.replyDraft : '')
  useEffect(() => {
    if (location.state?.replyDraft) navigate(location.pathname, { replace: true, state: null })
  }, [location, navigate])
  return <MissionThread mission={useOutletMission()} initialDraft={draft} />
}
