import { useEffect, useState } from 'react'
import { useApi } from '../api/context'
import type { Api } from '../api/index'
import type { Dataset, Mission } from '../types'

/** Loads on mount and again after every api change. `undefined` until the first load resolves. */
function useApiData<T>(load: (api: Api) => Promise<T>): T | undefined {
  const api = useApi()
  const [data, setData] = useState<T>()

  useEffect(() => {
    let cancelled = false
    const run = () => {
      load(api).then((value) => {
        if (!cancelled) setData(value)
      })
    }
    run()
    const unsubscribe = api.subscribe(run)
    return () => {
      cancelled = true
      unsubscribe()
    }
  }, [api, load])

  return data
}

const loadMissions = (api: Api) => api.listMissions()
const loadDatasets = (api: Api) => api.listDatasets()

export function useMissions(): Mission[] | undefined {
  return useApiData(loadMissions)
}

export function useDatasets(): Dataset[] | undefined {
  return useApiData(loadDatasets)
}

export function useMission(id: string): { mission?: Mission; loading: boolean } {
  const api = useApi()
  const [state, setState] = useState<{ id: string; mission?: Mission }>()

  useEffect(() => {
    let cancelled = false
    const run = () => {
      api.getMission(id).then((mission) => {
        if (!cancelled) setState({ id, mission })
      })
    }
    run()
    const unsubscribe = api.subscribe(run)
    return () => {
      cancelled = true
      unsubscribe()
    }
  }, [api, id])

  // A result for a previous id is stale, not an answer for this one.
  const current = state?.id === id ? state : undefined
  return { mission: current?.mission, loading: !current }
}
