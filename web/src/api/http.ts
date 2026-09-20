import type { Dataset, Meta, Mission, MissionSummary, ResearchFinding } from '../types'
import { ValidationError, type Api } from './index'

const POLL_MS = 2000
const UNREACHABLE = 'unreachable'

/** Fetch-backed Api. The server has no push channel, so `subscribe` is driven by one shared poll. */
export function createHttpApi(baseUrl = ''): Api {
  const listeners = new Set<() => void>()
  let timer: ReturnType<typeof setInterval> | undefined
  let polling = false
  let lastSeen: string | undefined
  // The mission opened last is polled alongside the list, whose summaries do not carry the thread.
  let watchedId: string | undefined

  const notify = () => listeners.forEach((listener) => listener())

  async function send(path: string, body?: unknown): Promise<Response> {
    const init = body === undefined ? undefined : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
    const response = await fetch(`${baseUrl}/api${path}`, init)
    if (response.status === 422) {
      const { field, message } = await response.json()
      throw new ValidationError(field, message)
    }
    return response
  }

  async function read<T>(response: Response): Promise<T> {
    if (!response.ok) throw new Error(`Request failed with status ${response.status}`)
    return response.json()
  }

  async function change<T>(path: string, body: unknown): Promise<T> {
    const result = await read<T>(await send(path, body))
    notify()
    return result
  }

  const listMissions = async () => read<MissionSummary[]>(await send('/missions'))

  async function getMission(id: string) {
    const response = await send(`/missions/${encodeURIComponent(id)}`)
    return response.status === 404 ? undefined : read<Mission>(response)
  }

  async function snapshot(): Promise<string> {
    try {
      return JSON.stringify(await Promise.all([listMissions(), watchedId ? getMission(watchedId) : undefined]))
    } catch {
      // One notification on the way into an outage and one on the way out lets listeners show, then clear, a reconnecting state.
      return UNREACHABLE
    }
  }

  async function poll() {
    if (polling) return
    polling = true
    const seen = await snapshot()
    polling = false
    if (seen === lastSeen) return
    lastSeen = seen
    notify()
  }

  return {
    async getMeta() {
      return read<Meta>(await send('/meta'))
    },

    listMissions,

    async getMission(id) {
      watchedId = id
      return getMission(id)
    },

    async createMission(input) {
      return change<Mission>('/missions', input)
    },

    async sendMessage(id, text) {
      await change(`/missions/${encodeURIComponent(id)}/messages`, { text })
    },

    async markDone(id) {
      await change(`/missions/${encodeURIComponent(id)}/done`, {})
    },

    async generateReport(id) {
      await change(`/missions/${encodeURIComponent(id)}/report`, {})
    },

    async buildExplorer(id, instructions) {
      const trimmed = instructions?.trim()
      await change(`/missions/${encodeURIComponent(id)}/explorer`, trimmed ? { instructions: trimmed } : {})
    },

    async listDatasets() {
      return read<Dataset[]>(await send('/datasets'))
    },

    async listResearch() {
      return read<ResearchFinding[]>(await send('/research'))
    },

    async linkDataset(input) {
      return change<Dataset>('/datasets', input)
    },

    subscribe(listener) {
      listeners.add(listener)
      timer ??= setInterval(poll, POLL_MS)
      return () => {
        listeners.delete(listener)
        if (listeners.size > 0) return
        clearInterval(timer)
        timer = undefined
        lastSeen = undefined
      }
    },
  }
}
