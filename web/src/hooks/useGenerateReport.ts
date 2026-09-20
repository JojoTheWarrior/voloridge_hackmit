import { useApi } from '../api/context'
import type { Mission } from '../types'
import { useDevinRequest } from './useDevinRequest'

/** Asks for a mission's report. `busy` covers the request itself and the wait for Devin. */
export function useGenerateReport(mission: Mission): { busy: boolean; generate: () => Promise<void> } {
  const api = useApi()
  const { busy, request } = useDevinRequest(mission, mission.reportPending, () => api.generateReport(mission.id))

  async function generate() {
    try {
      await request()
    } catch {
      // Nothing changed; the control is still there to try again.
    }
  }

  return { busy, generate }
}
