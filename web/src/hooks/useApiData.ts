import { useEffect, useState } from 'react'
import { useApi } from '../api/context'
import type { Api } from '../api/index'
import type { Dataset, Meta, Mission, MissionSummary } from '../types'

/** Loads on mount and again after every api change. `undefined` until the first load resolves; a failed reload keeps the last value. */
function useApiData<T>(load: (api: Api) => Promise<T>) {
  const api = useApi()
  const [data, setData] = useState<T>()
  const [reconnecting, setReconnecting] = useState(false)

  useEffect(() => {
    let cancelled = false
    let sequence = 0
    const run = () => {
      const request = ++sequence
      load(api).then(
        (value) => {
          if (!cancelled && request === sequence) {
            setData(value)
            setReconnecting(false)
          }
        },
        () => { if (!cancelled && request === sequence) setReconnecting(true) },
      )
    }
    run()
    const unsubscribe = api.subscribe(run)
    return () => {
      cancelled = true
      unsubscribe()
    }
  }, [api, load])

  return { data, reconnecting }
}

const loadMissions = (api: Api) => api.listMissions()
const loadDatasets = (api: Api) => api.listDatasets()

export function useMissions(): MissionSummary[] | undefined {
  return useApiData(loadMissions).data
}

export function useDatasets(): Dataset[] | undefined {
  return useApiData(loadDatasets).data
}

export function useDatasetState() {
  return useApiData(loadDatasets)
}

/** Whether the server is in demo mode cannot change while the page is open, so this loads once. */
export function useMeta(): Meta | undefined {
  const api = useApi()
  const [meta, setMeta] = useState<Meta>()

  useEffect(() => {
    let cancelled = false
    api.getMeta().then(
      (value) => {
        if (!cancelled) setMeta(value)
      },
      () => {},
    )
    return () => {
      cancelled = true
    }
  }, [api])

  return meta
}

interface MissionState {
  id: string
  loaded: boolean
  mission?: Mission
  reconnecting: boolean
}

/** `reconnecting` is set while reads fail; the last thread that did load stays in place meanwhile. */
export function useMission(id: string): { mission?: Mission; loading: boolean; reconnecting: boolean } {
  const api = useApi()
  const [state, setState] = useState<MissionState>()

  useEffect(() => {
    let cancelled = false
    const run = () => {
      api.getMission(id).then(
        (mission) => {
          if (!cancelled) setState({ id, loaded: true, mission, reconnecting: false })
        },
        () => {
          if (!cancelled) setState((last) => ({ ...(last?.id === id ? last : { id, loaded: false }), reconnecting: true }))
        },
      )
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
  return { mission: current?.mission, loading: !current?.loaded, reconnecting: current?.reconnecting ?? false }
}
