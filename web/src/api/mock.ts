import type { Dataset, Mission, MissionSummary } from '../types'
import { seedDatasets, seedMissions } from './fixtures'
import { ValidationError, type Api } from './index'
import { applyBeat, REPLY_BEAT, SCRIPT, type Beat } from './script'

const TITLE_MAX = 48

interface MockOptions {
  stepMs?: number
  demo?: boolean
  seed?: { missions: Mission[]; datasets: Dataset[] }
}

function deriveTitle(hypothesis: string): string {
  const clean = hypothesis.replace(/[?.!]+$/, '')
  if (clean.length <= TITLE_MAX) return clean
  const cut = clean.lastIndexOf(' ', TITLE_MAX)
  return clean.slice(0, cut > 0 ? cut : TITLE_MAX)
}

function isHttpUrl(value: string): boolean {
  try {
    return ['http:', 'https:'].includes(new URL(value).protocol)
  } catch {
    return false
  }
}

function summaryOf({ id, title, hypothesis, status, createdAt, updatedAt }: Mission): MissionSummary {
  return { id, title, hypothesis, status, createdAt, updatedAt }
}

/** In-memory Api that plays a scripted research run into each working mission on a timer. */
export function createMockApi({ stepMs = 2500, demo = false, seed }: MockOptions = {}): Api {
  const missions = structuredClone(seed?.missions ?? seedMissions())
  const datasets = structuredClone(seed?.datasets ?? seedDatasets())
  const listeners = new Set<() => void>()
  // Beats still to play per mission. A mission works while its queue drains and waits once it is empty.
  const queues = new Map<string, Beat[]>()
  const timers = new Map<string, ReturnType<typeof setTimeout>>()
  let nextId = 1

  const notify = () => listeners.forEach((listener) => listener())

  function find(id: string): Mission {
    const mission = missions.find((m) => m.id === id)
    if (!mission) throw new Error('Mission not found')
    return mission
  }

  function play(mission: Mission) {
    if (timers.has(mission.id) || !queues.get(mission.id)?.length) return
    timers.set(
      mission.id,
      setTimeout(() => {
        timers.delete(mission.id)
        const queue = queues.get(mission.id)!
        applyBeat(mission, queue.shift()!, new Date().toISOString())
        if (queue.length === 0) mission.status = 'waiting'
        play(mission)
        notify()
      }, stepMs),
    )
  }

  function enqueue(mission: Mission, beats: Beat[]) {
    queues.set(mission.id, [...(queues.get(mission.id) ?? []), ...beats])
    play(mission)
  }

  for (const mission of missions.filter((m) => m.status === 'working')) {
    // Every beat adds one event, so the thread length says how far a seeded run has got.
    const played = mission.events.filter((e) => e.kind !== 'user_message' && e.kind !== 'error').length
    enqueue(mission, SCRIPT.slice(played))
  }

  return {
    async getMeta() {
      return { demo }
    },

    async listMissions() {
      return missions.map(summaryOf).sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt))
    },

    async getMission(id) {
      return structuredClone(missions.find((m) => m.id === id))
    },

    async createMission({ hypothesis, datasetIds }) {
      const trimmed = hypothesis.trim()
      if (!trimmed) throw new ValidationError('hypothesis', 'Describe a connection to test')
      const now = new Date().toISOString()
      const mission: Mission = {
        id: `m-${nextId++}`,
        title: deriveTitle(trimmed),
        hypothesis: trimmed,
        status: 'working',
        createdAt: now,
        updatedAt: now,
        datasetIds: [...datasetIds],
        events: [{ id: 'e1', at: now, kind: 'user_message', text: trimmed }],
      }
      missions.unshift(mission)
      enqueue(mission, SCRIPT)
      notify()
      return structuredClone(mission)
    },

    async sendMessage(id, text) {
      const mission = find(id)
      const trimmed = text.trim()
      if (!trimmed) throw new ValidationError('text', 'Write a reply')
      const now = new Date().toISOString()
      mission.events.push({ id: `e${mission.events.length + 1}`, at: now, kind: 'user_message', text: trimmed })
      mission.updatedAt = now
      mission.status = 'working'
      delete mission.needsUser
      enqueue(mission, [REPLY_BEAT])
      notify()
    },

    async markDone(id) {
      const mission = find(id)
      clearTimeout(timers.get(id))
      timers.delete(id)
      queues.delete(id)
      mission.status = 'done'
      delete mission.needsUser
      notify()
    },

    async listDatasets() {
      return structuredClone(datasets)
    },

    async linkDataset(input) {
      const name = input.name.trim()
      const url = input.url.trim()
      if (!name) throw new ValidationError('name', 'Enter a name')
      if (!isHttpUrl(url)) throw new ValidationError('url', 'Enter an http or https URL')
      const dataset: Dataset = {
        id: `d-${nextId++}`,
        name,
        url,
        kind: 'other',
        seriesCount: 0,
        dateRange: '',
        syncedAt: new Date().toISOString(),
      }
      datasets.unshift(dataset)
      notify()
      return structuredClone(dataset)
    },

    subscribe(listener) {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
  }
}
