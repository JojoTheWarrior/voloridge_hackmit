import { STEP_KEYS } from '../steps'
import { ValidationError } from './index'
import { createMockApi, SEED_SLOWDOWN } from './mock'

const STEP_MS = 1000

function activeKey(steps: { key: string; state: string }[]) {
  return steps.find((s) => s.state === 'active')?.key
}

describe('mock api', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  const empty = { missions: [], datasets: [] }

  it('lists seeded missions newest first', async () => {
    const api = createMockApi()
    const missions = await api.listMissions()
    expect(missions.length).toBeGreaterThan(0)
    const times = missions.map((m) => Date.parse(m.createdAt))
    expect(times).toEqual([...times].sort((a, b) => b - a))
  })

  it('seeds running, done and failed missions', async () => {
    const statuses = new Set((await createMockApi().listMissions()).map((m) => m.status))
    expect(statuses).toEqual(new Set(['running', 'done', 'failed']))
  })

  it('creates a running mission with the plan step active', async () => {
    const api = createMockApi({ stepMs: STEP_MS, seed: empty })
    const mission = await api.createMission({ hypothesis: '  Does wind move PM2.5?  ', datasetIds: ['d1'] })
    expect(mission.status).toBe('running')
    expect(mission.hypothesis).toBe('Does wind move PM2.5?')
    expect(mission.title).toBe('Does wind move PM2.5')
    expect(mission.datasetIds).toEqual(['d1'])
    expect(activeKey(mission.steps)).toBe('plan')
    expect(mission.steps.filter((s) => s.state === 'pending')).toHaveLength(4)
    expect((await api.listMissions())[0].id).toBe(mission.id)
  })

  it('truncates long titles at a word boundary', async () => {
    const api = createMockApi({ seed: empty })
    const hypothesis = 'Do shipping delays in the Strait of Hormuz lead moves in Brent crude futures by several days?'
    const { title } = await api.createMission({ hypothesis, datasetIds: [] })
    expect(title.length).toBeLessThanOrEqual(48)
    expect(hypothesis.startsWith(title)).toBe(true)
    expect(hypothesis[title.length]).toBe(' ')
  })

  it('walks through every step then finishes with a result', async () => {
    const api = createMockApi({ stepMs: STEP_MS, seed: empty })
    const { id } = await api.createMission({ hypothesis: 'A leads B', datasetIds: [] })
    for (const key of STEP_KEYS.slice(1)) {
      vi.advanceTimersByTime(STEP_MS)
      const m = await api.getMission(id)
      expect(m?.status).toBe('running')
      expect(activeKey(m!.steps)).toBe(key)
    }
    vi.advanceTimersByTime(STEP_MS)
    const done = await api.getMission(id)
    expect(done?.status).toBe('done')
    expect(done?.steps.every((s) => s.state === 'done')).toBe(true)
    expect(done?.result?.points.length).toBeGreaterThan(10)
    expect(done?.elapsedSeconds).toBeGreaterThan(0)

    vi.advanceTimersByTime(STEP_MS * 3)
    expect((await api.getMission(id))?.elapsedSeconds).toBe(done?.elapsedSeconds)
  })

  it('gives the same result for the same hypothesis', async () => {
    const api = createMockApi({ stepMs: STEP_MS, seed: empty })
    const a = await api.createMission({ hypothesis: 'A leads B', datasetIds: [] })
    const b = await api.createMission({ hypothesis: 'A leads B', datasetIds: [] })
    vi.advanceTimersByTime(STEP_MS * 5)
    expect((await api.getMission(a.id))?.result).toEqual((await api.getMission(b.id))?.result)
    expect(a.id).not.toBe(b.id)
  })

  it('advances seeded running missions', async () => {
    const api = createMockApi({ stepMs: STEP_MS })
    const running = (await api.listMissions()).filter((m) => m.status === 'running')
    expect(running.length).toBeGreaterThan(0)
    vi.advanceTimersByTime(STEP_MS * 5)
    expect((await api.listMissions()).filter((m) => m.status === 'running')).toHaveLength(running.length)
    vi.advanceTimersByTime(STEP_MS * 5 * SEED_SLOWDOWN)
    expect((await api.listMissions()).filter((m) => m.status === 'running')).toHaveLength(0)
  })

  it('notifies subscribers until they unsubscribe', async () => {
    const api = createMockApi({ stepMs: STEP_MS, seed: empty })
    const listener = vi.fn()
    const unsubscribe = api.subscribe(listener)
    await api.createMission({ hypothesis: 'A leads B', datasetIds: [] })
    expect(listener).toHaveBeenCalledTimes(1)
    vi.advanceTimersByTime(STEP_MS)
    expect(listener).toHaveBeenCalledTimes(2)
    unsubscribe()
    vi.advanceTimersByTime(STEP_MS)
    expect(listener).toHaveBeenCalledTimes(2)
  })

  it.each(['', '   ', '\n\t'])('rejects blank hypothesis %j', async (hypothesis) => {
    const api = createMockApi({ seed: empty })
    const error = await api.createMission({ hypothesis, datasetIds: [] }).catch((e) => e)
    expect(error).toBeInstanceOf(ValidationError)
    expect(error.field).toBe('hypothesis')
    expect(await api.listMissions()).toHaveLength(0)
  })

  it('resolves undefined for an unknown mission', async () => {
    expect(await createMockApi().getMission('nope')).toBeUndefined()
  })

  it('returns copies, not store references', async () => {
    const api = createMockApi()
    const [first] = await api.listMissions()
    first.title = 'mutated'
    first.steps[0].state = 'pending'
    const again = await api.getMission(first.id)
    expect(again?.title).not.toBe('mutated')
    expect(again?.steps[0].state).not.toBe('pending')
  })

  describe('linkDataset', () => {
    it('adds a trimmed dataset at the top and notifies', async () => {
      const api = createMockApi()
      const listener = vi.fn()
      api.subscribe(listener)
      const before = (await api.listDatasets()).length
      const dataset = await api.linkDataset({ name: '  FRED  ', url: ' https://fred.stlouisfed.org ' })
      expect(dataset.name).toBe('FRED')
      expect(dataset.url).toBe('https://fred.stlouisfed.org')
      const after = await api.listDatasets()
      expect(after).toHaveLength(before + 1)
      expect(after[0].id).toBe(dataset.id)
      expect(listener).toHaveBeenCalledTimes(1)
    })

    it('accepts http urls', async () => {
      await expect(createMockApi().linkDataset({ name: 'x', url: 'http://example.com/data' })).resolves.toBeDefined()
    })

    it('rejects an empty name', async () => {
      const error = await createMockApi().linkDataset({ name: '  ', url: 'https://x.com' }).catch((e) => e)
      expect(error).toBeInstanceOf(ValidationError)
      expect(error.field).toBe('name')
    })

    it.each(['ftp://x.com', 'not a url', '', 'javascript:alert(1)'])('rejects url %j', async (url) => {
      const api = createMockApi()
      const before = (await api.listDatasets()).length
      const error = await api.linkDataset({ name: 'x', url }).catch((e) => e)
      expect(error).toBeInstanceOf(ValidationError)
      expect(error.field).toBe('url')
      expect(await api.listDatasets()).toHaveLength(before)
    })
  })
})
