import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { ApiProvider } from '../api/ApiProvider'
import type { Api } from '../api/index'
import { createMockApi } from '../api/mock'
import { makeMission } from '../test/missions'
import { useMeta, useMission, useMissions } from './useApiData'

function wrapperFor(api: Api) {
  return ({ children }: { children: ReactNode }) => <ApiProvider api={api}>{children}</ApiProvider>
}

/** A mock api whose listeners can be poked by hand and whose reads can be made to fail. */
function flakyApi(...missions: ReturnType<typeof makeMission>[]) {
  const inner = createMockApi({ seed: { missions, datasets: [] } })
  const listeners = new Set<() => void>()
  const state = { down: false }
  const guard = <A extends unknown[], R>(call: (...args: A) => Promise<R>) => (...args: A) =>
    state.down ? Promise.reject(new TypeError('Failed to fetch')) : call(...args)
  const api: Api = {
    ...inner,
    getMeta: guard(inner.getMeta),
    listMissions: guard(inner.listMissions),
    getMission: guard(inner.getMission),
    subscribe(listener) {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
  }
  return { api, state, listeners, poke: () => act(async () => listeners.forEach((l) => l())) }
}

describe('useMission', () => {
  it('loads a mission, then reports an unknown id as missing rather than loading', async () => {
    const mission = makeMission('done')
    const { api } = flakyApi(mission)
    const { result, rerender } = renderHook(({ id }) => useMission(id), { wrapper: wrapperFor(api), initialProps: { id: mission.id } })
    expect(result.current).toEqual({ mission: undefined, loading: true, reconnecting: false })
    await waitFor(() => expect(result.current.mission?.id).toBe(mission.id))
    expect(result.current.loading).toBe(false)

    rerender({ id: 'nope' })
    expect(result.current).toEqual({ mission: undefined, loading: true, reconnecting: false })
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.mission).toBeUndefined()
  })

  it('keeps the last thread and flags reconnecting while reads fail, then recovers', async () => {
    const mission = makeMission('waiting')
    const { api, state, poke } = flakyApi(mission)
    const { result } = renderHook(() => useMission(mission.id), { wrapper: wrapperFor(api) })
    await waitFor(() => expect(result.current.loading).toBe(false))

    state.down = true
    await poke()
    expect(result.current.reconnecting).toBe(true)
    expect(result.current.mission?.id).toBe(mission.id)

    state.down = false
    await api.markDone(mission.id)
    await poke()
    expect(result.current.reconnecting).toBe(false)
    expect(result.current.mission?.status).toBe('done')
  })

  it('stays loading when the very first read fails', async () => {
    const mission = makeMission('waiting')
    const { api, state, poke } = flakyApi(mission)
    state.down = true
    const { result } = renderHook(() => useMission(mission.id), { wrapper: wrapperFor(api) })
    await waitFor(() => expect(result.current.reconnecting).toBe(true))
    expect(result.current.loading).toBe(true)

    state.down = false
    await poke()
    expect(result.current).toMatchObject({ loading: false, reconnecting: false })
  })

  it('unsubscribes on unmount', async () => {
    const mission = makeMission('waiting')
    const { api, listeners } = flakyApi(mission)
    const { unmount } = renderHook(() => useMission(mission.id), { wrapper: wrapperFor(api) })
    expect(listeners.size).toBe(1)
    unmount()
    expect(listeners.size).toBe(0)
  })
})

describe('useMissions', () => {
  it('keeps the last list when a reload fails', async () => {
    const { api, state, poke } = flakyApi(makeMission('done'), makeMission('waiting'))
    const { result } = renderHook(() => useMissions(), { wrapper: wrapperFor(api) })
    await waitFor(() => expect(result.current).toHaveLength(2))
    state.down = true
    await poke()
    expect(result.current).toHaveLength(2)
  })
})

describe('useMeta', () => {
  it('loads once and does not reload on changes', async () => {
    const { api, poke } = flakyApi()
    const getMeta = vi.spyOn(api, 'getMeta')
    const { result } = renderHook(() => useMeta(), { wrapper: wrapperFor(api) })
    await waitFor(() => expect(result.current).toEqual({ demo: false }))
    await poke()
    expect(getMeta).toHaveBeenCalledTimes(1)
  })

  it('stays undefined when the server cannot be reached', async () => {
    const { api, state } = flakyApi()
    state.down = true
    const { result } = renderHook(() => useMeta(), { wrapper: wrapperFor(api) })
    await act(async () => {})
    expect(result.current).toBeUndefined()
  })
})
