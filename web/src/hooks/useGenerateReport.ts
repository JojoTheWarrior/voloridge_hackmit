import { useApi } from '../api/context'
import { useState } from 'react'
import type { Mission } from '../types'
import { useDevinRequest } from './useDevinRequest'

/** Asks for a mission's report. `busy` covers the request itself and the wait for Devin. */
export function useGenerateReport(mission: Mission) {
  const api = useApi()
  const [error, setError] = useState('')
  const { busy, request } = useDevinRequest(mission, mission.reportPending, () => api.generateReport(mission.id))

  async function generate() {
    setError('')
    try {
      await request()
    } catch {
      setError('The report request didn’t send. Check your connection and try again.')
    }
  }

  return { busy, generate, error }
}
