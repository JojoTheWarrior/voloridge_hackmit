import { useRef, useState } from 'react'
import type { Mission } from '../types'

/**
 * One request to Devin at a time. `busy` runs from the click until a newer snapshot of the mission says what came of it,
 * so there is no gap between the request landing and `pending` showing up for a second click to slip through.
 * A failed request rejects, so whoever asked can say why.
 */
export function useDevinRequest<Args extends unknown[]>(mission: Mission, pending: boolean, send: (...args: Args) => Promise<void>) {
  const [heldFor, setHeldFor] = useState<Mission>()
  // State lags a render behind; the ref is what stops a second click in the same tick.
  const locked = useRef(false)
  const busy = heldFor === mission || pending

  async function request(...args: Args) {
    if (locked.current || busy) return
    locked.current = true
    setHeldFor(mission)
    try {
      await send(...args)
    } catch (caught) {
      setHeldFor(undefined)
      throw caught
    } finally {
      locked.current = false
    }
  }

  return { busy, request }
}
