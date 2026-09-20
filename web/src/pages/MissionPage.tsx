import { MissionThread } from '../components/thread/MissionThread'
import { useOutletMission } from '../hooks/useOutletMission'

export function MissionPage() {
  return <MissionThread mission={useOutletMission()} />
}
