import { useRef, useState } from 'react'
import { useApi } from '../api/context'
import type { Mission } from '../types'

/** Asks for a mission's report at most once at a time. `busy` covers the request itself and the wait for Devin. */
export function useGenerateReport(mission: Pick<Mission, 'id' | 'reportPending'>): { busy: boolean; generate: () => Promise<void> } {
  const api = useApi()
  const [asking, setAsking] = useState(false)
  // State lags a render behind; the ref is what stops a second click in the same tick.
  const locked = useRef(false)

  async function generate() {
    if (locked.current || mission.reportPending) return
    locked.current = true
    setAsking(true)
    try {
      await api.generateReport(mission.id)
    } catch {
      // Nothing changed; the control is still there to try again.
    } finally {
      locked.current = false
      setAsking(false)
    }
  }

  return { busy: asking || mission.reportPending, generate }
}
