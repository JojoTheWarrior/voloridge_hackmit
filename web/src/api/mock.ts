import { STEP_KEYS, stepsAt } from '../steps'
import type { Dataset, Mission } from '../types'
import { buildResult, seedDatasets, seedMissions } from './fixtures'
import { ValidationError, type Api } from './index'

const TITLE_MAX = 48
// Mock time: each step pretends to have taken this long, whatever stepMs is.
const SECONDS_PER_STEP = 53

interface MockOptions {
  stepMs?: number
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

/** In-memory Api that walks running missions through their steps on a timer. */
export function createMockApi({ stepMs = 2500, seed }: MockOptions = {}): Api {
  const missions = structuredClone(seed?.missions ?? seedMissions())
  const datasets = structuredClone(seed?.datasets ?? seedDatasets())
  const listeners = new Set<() => void>()
  let nextId = 1

  const notify = () => listeners.forEach((listener) => listener())

  function advance(mission: Mission) {
    const active = mission.steps.findIndex((s) => s.state === 'active')
    const next = STEP_KEYS[active + 1]
    mission.elapsedSeconds += SECONDS_PER_STEP
    mission.steps = stepsAt(next)
    if (next) {
      setTimeout(() => advance(mission), stepMs)
    } else {
      mission.status = 'done'
      mission.result = buildResult(mission.hypothesis)
    }
    notify()
  }

  missions.filter((m) => m.status === 'running').forEach((m) => setTimeout(() => advance(m), stepMs))

  return {
    async listMissions() {
      return structuredClone(missions).sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt))
    },

    async getMission(id) {
      return structuredClone(missions.find((m) => m.id === id))
    },

    async createMission({ hypothesis, datasetIds }) {
      const trimmed = hypothesis.trim()
      if (!trimmed) throw new ValidationError('hypothesis', 'Describe a connection to test')
      const mission: Mission = {
        id: `m-${nextId++}`,
        title: deriveTitle(trimmed),
        hypothesis: trimmed,
        status: 'running',
        datasetIds: [...datasetIds],
        createdAt: new Date().toISOString(),
        elapsedSeconds: 0,
        steps: stepsAt('plan'),
      }
      missions.unshift(mission)
      setTimeout(() => advance(mission), stepMs)
      notify()
      return structuredClone(mission)
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
