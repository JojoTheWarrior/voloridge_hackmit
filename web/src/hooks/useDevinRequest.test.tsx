import { act, renderHook } from '@testing-library/react'
import { makeMission } from '../test/missions'
import type { Mission } from '../types'
import { useDevinRequest } from './useDevinRequest'

function renderRequest(send: () => Promise<void>, first = makeMission('waiting')) {
  return renderHook(({ mission, pending }: { mission: Mission; pending: boolean }) => useDevinRequest(mission, pending, send), {
    initialProps: { mission: first, pending: false },
  })
}

describe('useDevinRequest', () => {
  it('is busy from the request until a newer snapshot of the mission arrives', async () => {
    const mission = makeMission('waiting')
    const { result, rerender } = renderRequest(async () => {}, mission)
    expect(result.current.busy).toBe(false)
    await act(() => result.current.request())
    expect(result.current.busy).toBe(true)
    rerender({ mission: { ...mission }, pending: false })
    expect(result.current.busy).toBe(false)
  })

  it('stays busy for as long as the mission says Devin is on it', async () => {
    const mission = makeMission('waiting')
    const { result, rerender } = renderRequest(async () => {}, mission)
    await act(() => result.current.request())
    rerender({ mission: { ...mission }, pending: true })
    expect(result.current.busy).toBe(true)
    rerender({ mission: { ...mission }, pending: false })
    expect(result.current.busy).toBe(false)
  })

  it('sends once, however often it is asked before the mission catches up', async () => {
    const send = vi.fn(async () => {})
    const { result } = renderRequest(send)
    await act(async () => {
      result.current.request()
      result.current.request()
    })
    await act(() => result.current.request())
    expect(send).toHaveBeenCalledTimes(1)
  })

  it('sends nothing while Devin is already on it', async () => {
    const send = vi.fn(async () => {})
    const mission = makeMission('working')
    const { result } = renderHook(() => useDevinRequest(mission, true, send))
    await act(() => result.current.request())
    expect(send).not.toHaveBeenCalled()
  })

  it('rejects and frees up again when the request fails', async () => {
    const send = vi.fn().mockRejectedValueOnce(new TypeError('Failed to fetch')).mockResolvedValueOnce(undefined)
    const { result } = renderRequest(send)
    let caught: unknown
    await act(() => result.current.request().catch((error) => (caught = error)))
    expect(caught).toBeInstanceOf(TypeError)
    expect(result.current.busy).toBe(false)
    await act(() => result.current.request())
    expect(send).toHaveBeenCalledTimes(2)
  })

  it('passes its arguments through', async () => {
    const send = vi.fn<(instructions: string) => Promise<void>>(async () => {})
    const mission = makeMission('waiting')
    const { result } = renderHook(() => useDevinRequest(mission, false, send))
    await act(() => result.current.request('Add a legend'))
    expect(send).toHaveBeenCalledExactlyOnceWith('Add a legend')
  })
})
