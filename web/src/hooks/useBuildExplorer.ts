import { useApi } from '../api/context'
import type { Mission } from '../types'
import { useDevinRequest } from './useDevinRequest'

/** Asks for a build, or with instructions for a change. `busy` covers the request itself and the wait for Devin. */
export function useBuildExplorer(mission: Mission): { busy: boolean; build: (instructions: string) => Promise<void> } {
  const api = useApi()
  const { busy, request } = useDevinRequest(mission, mission.explorerPending, (instructions: string) => api.buildExplorer(mission.id, instructions))
  return { busy, build: request }
}
