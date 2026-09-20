import { useOutletContext } from 'react-router-dom'
import type { Mission } from '../types'

/** The mission loaded by `MissionLayout`, for whichever of its views is showing. */
export function useOutletMission(): Mission {
  return useOutletContext<Mission>()
}
