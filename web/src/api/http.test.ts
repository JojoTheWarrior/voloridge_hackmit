import { makeMission } from '../test/missions'
import { createHttpApi } from './http'
import { ValidationError } from './index'

type Handler = (init?: RequestInit) => Response | Promise<Response>

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status })

/** Stubs fetch with one handler per "METHOD path"; anything else is a test bug. */
function stubFetch(routes: Record<string, Handler>) {
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const key = `${init?.method ?? 'GET'} ${url}`
    if (!routes[key]) throw new Error(`Unexpected request: ${key}`)
    return routes[key](init)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

const requests = (fetchMock: ReturnType<typeof stubFetch>) => fetchMock.mock.calls.map(([url, init]) => `${init?.method ?? 'GET'} ${url}`)

describe('http api', () => {
  afterEach(() => vi.unstubAllGlobals())

  describe('requests', () => {
    it('reads meta, missions and datasets', async () => {
      const mission = makeMission('waiting')
      stubFetch({
        'GET /api/meta': () => json({ demo: true }),
        'GET /api/missions': () => json([mission]),
        'GET /api/datasets': () => json([{ id: 'd1' }]),
      })
      const api = createHttpApi()
      expect(await api.getMeta()).toEqual({ demo: true })
      expect(await api.listMissions()).toEqual([mission])
      expect(await api.listDatasets()).toEqual([{ id: 'd1' }])
    })

    it('prefixes a base url', async () => {
      const fetchMock = stubFetch({ 'GET http://host:8030/api/meta': () => json({ demo: false }) })
      await createHttpApi('http://host:8030').getMeta()
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })

    it('reads one mission, escaping its id', async () => {
      const mission = makeMission('working')
      stubFetch({ 'GET /api/missions/a%2Fb': () => json(mission) })
      expect(await createHttpApi().getMission('a/b')).toEqual(mission)
    })

    it('resolves undefined for a mission the server does not know', async () => {
      stubFetch({ 'GET /api/missions/nope': () => json({ message: 'Mission not found' }, 404) })
      expect(await createHttpApi().getMission('nope')).toBeUndefined()
    })

    it('creates a mission, passing the reference along', async () => {
      const mission = makeMission('working')
      const fetchMock = stubFetch({ 'POST /api/missions': () => json(mission, 201) })
      const input = { hypothesis: 'A leads B', datasetIds: ['gdelt'], reference: 'notes' }
      expect(await createHttpApi().createMission(input)).toEqual(mission)
      const init = fetchMock.mock.calls[0][1]
      expect(init?.headers).toEqual({ 'Content-Type': 'application/json' })
      expect(JSON.parse(init?.body as string)).toEqual(input)
    })

    it('sends a reply and resolves with nothing', async () => {
      const fetchMock = stubFetch({ 'POST /api/missions/m1/messages': () => json({}, 202) })
      expect(await createHttpApi().sendMessage('m1', 'Drop it')).toBeUndefined()
      expect(JSON.parse(fetchMock.mock.calls[0][1]?.body as string)).toEqual({ text: 'Drop it' })
    })

    it('marks a mission done', async () => {
      const fetchMock = stubFetch({ 'POST /api/missions/m1/done': () => json({}) })
      expect(await createHttpApi().markDone('m1')).toBeUndefined()
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })

    it('asks for a report with an empty post, escaping the id', async () => {
      const fetchMock = stubFetch({ 'POST /api/missions/a%2Fb/report': () => json({}, 202) })
      expect(await createHttpApi().generateReport('a/b')).toBeUndefined()
      expect(fetchMock).toHaveBeenCalledTimes(1)
      expect(JSON.parse(fetchMock.mock.calls[0][1]?.body as string)).toEqual({})
    })

    it('asks for an explorer with an empty post when there are no instructions, escaping the id', async () => {
      const fetchMock = stubFetch({ 'POST /api/missions/a%2Fb/explorer': () => json({}, 202) })
      expect(await createHttpApi().buildExplorer('a/b')).toBeUndefined()
      expect(fetchMock).toHaveBeenCalledTimes(1)
      expect(JSON.parse(fetchMock.mock.calls[0][1]?.body as string)).toEqual({})
    })

    it.each(['', '   ', '\n\t'])('leaves blank instructions %j out of the explorer request', async (instructions) => {
      const fetchMock = stubFetch({ 'POST /api/missions/m1/explorer': () => json({}, 202) })
      await createHttpApi().buildExplorer('m1', instructions)
      expect(JSON.parse(fetchMock.mock.calls[0][1]?.body as string)).toEqual({})
    })

    it('passes instructions for the explorer along', async () => {
      const fetchMock = stubFetch({ 'POST /api/missions/m1/explorer': () => json({}, 202) })
      await createHttpApi().buildExplorer('m1', ' Add a heatmap layer ')
      expect(JSON.parse(fetchMock.mock.calls[0][1]?.body as string)).toEqual({ instructions: 'Add a heatmap layer' })
    })

    it('links a dataset', async () => {
      const fetchMock = stubFetch({ 'POST /api/datasets': () => json({ id: 'd9', name: 'FRED' }, 201) })
      expect(await createHttpApi().linkDataset({ name: 'FRED', url: 'https://fred.stlouisfed.org' })).toMatchObject({ id: 'd9' })
      expect(JSON.parse(fetchMock.mock.calls[0][1]?.body as string)).toEqual({ name: 'FRED', url: 'https://fred.stlouisfed.org' })
    })

    it.each([
      ['createMission', 'POST /api/missions', 'hypothesis', 'Describe a connection to test'],
      ['sendMessage', 'POST /api/missions/m1/messages', 'text', 'Write a reply'],
      ['linkDataset', 'POST /api/datasets', 'url', 'Enter an http or https URL'],
      ['buildExplorer', 'POST /api/missions/m1/explorer', 'text', 'Keep instructions under 2,000 characters'],
    ] as const)('maps a 422 from %s to a ValidationError', async (method, route, field, message) => {
      stubFetch({ [route]: () => json({ field, message }, 422) })
      const api = createHttpApi()
      const calls = {
        createMission: () => api.createMission({ hypothesis: '', datasetIds: [] }),
        sendMessage: () => api.sendMessage('m1', ''),
        linkDataset: () => api.linkDataset({ name: 'x', url: 'ftp://x' }),
        buildExplorer: () => api.buildExplorer('m1', 'x'.repeat(2001)),
      }
      const error = await calls[method]().catch((e) => e)
      expect(error).toBeInstanceOf(ValidationError)
      expect(error).toMatchObject({ field, message })
    })

    it.each([
      ['listMissions', 'GET /api/missions', 500],
      ['getMission', 'GET /api/missions/m1', 500],
      ['sendMessage', 'POST /api/missions/m1/messages', 404],
      ['markDone', 'POST /api/missions/m1/done', 404],
      ['generateReport', 'POST /api/missions/m1/report', 404],
      ['buildExplorer', 'POST /api/missions/m1/explorer', 404],
    ] as const)('rejects when %s gets an error status', async (method, route, status) => {
      stubFetch({ [route]: () => json({ message: 'nope' }, status) })
      const api = createHttpApi()
      const calls = {
        listMissions: () => api.listMissions(),
        getMission: () => api.getMission('m1'),
        sendMessage: () => api.sendMessage('m1', 'hi'),
        markDone: () => api.markDone('m1'),
        generateReport: () => api.generateReport('m1'),
        buildExplorer: () => api.buildExplorer('m1'),
      }
      const error = await calls[method]().catch((e) => e)
      expect(error).toBeInstanceOf(Error)
      expect(error).not.toBeInstanceOf(ValidationError)
      expect(error.message).toContain(String(status))
    })

    it('rejects when the network is down', async () => {
      stubFetch({ 'GET /api/missions': () => Promise.reject(new TypeError('Failed to fetch')) })
      await expect(createHttpApi().listMissions()).rejects.toThrow('Failed to fetch')
    })
  })

  describe('subscribe', () => {
    beforeEach(() => vi.useFakeTimers())
    afterEach(() => {
      expect(vi.getTimerCount()).toBe(0)
      vi.useRealTimers()
    })

    const POLL_MS = 2000

    function pollable() {
      const state = { missions: [makeMission('working')], down: false }
      const fetchMock = stubFetch({
        'GET /api/missions': () => (state.down ? Promise.reject(new TypeError('Failed to fetch')) : json(state.missions)),
        [`GET /api/missions/${state.missions[0].id}`]: () => json(state.missions[0]),
        'POST /api/missions/m1/done': () => json({}),
        'POST /api/missions/m1/report': () => json({}, 202),
        'POST /api/missions/m1/explorer': () => json({}, 202),
      })
      return { state, fetchMock, api: createHttpApi() }
    }

    it('does not poll until someone listens', async () => {
      const { fetchMock } = pollable()
      await vi.advanceTimersByTimeAsync(POLL_MS * 3)
      expect(fetchMock).not.toHaveBeenCalled()
    })

    it('polls every two seconds and notifies only when something changed', async () => {
      const { state, api } = pollable()
      const listener = vi.fn()
      const unsubscribe = api.subscribe(listener)

      await vi.advanceTimersByTimeAsync(POLL_MS - 1)
      expect(listener).not.toHaveBeenCalled()
      await vi.advanceTimersByTimeAsync(1)
      expect(listener).toHaveBeenCalledTimes(1)

      await vi.advanceTimersByTimeAsync(POLL_MS * 3)
      expect(listener).toHaveBeenCalledTimes(1)

      state.missions = [{ ...state.missions[0], status: 'waiting' }]
      await vi.advanceTimersByTimeAsync(POLL_MS)
      expect(listener).toHaveBeenCalledTimes(2)
      unsubscribe()
    })

    it('watches the mission that was opened last, not just the list', async () => {
      const { state, api } = pollable()
      const [mission] = state.missions
      await api.getMission(mission.id)
      const listener = vi.fn()
      const unsubscribe = api.subscribe(listener)
      await vi.advanceTimersByTimeAsync(POLL_MS)
      expect(listener).toHaveBeenCalledTimes(1)

      mission.events.push({ id: 'new', at: mission.updatedAt, kind: 'thought', text: 'A new thought' })
      await vi.advanceTimersByTimeAsync(POLL_MS)
      expect(listener).toHaveBeenCalledTimes(2)
      unsubscribe()
    })

    it('shares one poll between listeners and stops it with the last one', async () => {
      const { fetchMock, api } = pollable()
      const first = vi.fn()
      const second = vi.fn()
      const stopFirst = api.subscribe(first)
      const stopSecond = api.subscribe(second)
      expect(vi.getTimerCount()).toBe(1)

      await vi.advanceTimersByTimeAsync(POLL_MS)
      expect(requests(fetchMock)).toEqual(['GET /api/missions'])
      expect(first).toHaveBeenCalledTimes(1)
      expect(second).toHaveBeenCalledTimes(1)

      stopFirst()
      expect(vi.getTimerCount()).toBe(1)
      stopSecond()
      stopSecond()
      expect(vi.getTimerCount()).toBe(0)
      await vi.advanceTimersByTimeAsync(POLL_MS * 3)
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })

    it('polls again for a listener that arrives after the poll stopped', async () => {
      const { api } = pollable()
      api.subscribe(vi.fn())()
      const listener = vi.fn()
      const unsubscribe = api.subscribe(listener)
      await vi.advanceTimersByTimeAsync(POLL_MS)
      expect(listener).toHaveBeenCalledTimes(1)
      unsubscribe()
    })

    it('notifies once going into an outage and once coming out', async () => {
      const { state, api } = pollable()
      const listener = vi.fn()
      const unsubscribe = api.subscribe(listener)
      await vi.advanceTimersByTimeAsync(POLL_MS)
      expect(listener).toHaveBeenCalledTimes(1)

      state.down = true
      await vi.advanceTimersByTimeAsync(POLL_MS * 3)
      expect(listener).toHaveBeenCalledTimes(2)

      state.down = false
      await vi.advanceTimersByTimeAsync(POLL_MS)
      expect(listener).toHaveBeenCalledTimes(3)
      unsubscribe()
    })

    it('never overlaps a slow poll with the next one', async () => {
      let release = () => {}
      const fetchMock = stubFetch({
        'GET /api/missions': () => new Promise<Response>((resolve) => (release = () => resolve(json([])))),
      })
      const listener = vi.fn()
      const unsubscribe = createHttpApi().subscribe(listener)
      await vi.advanceTimersByTimeAsync(POLL_MS * 3)
      expect(fetchMock).toHaveBeenCalledTimes(1)

      release()
      await vi.advanceTimersByTimeAsync(POLL_MS)
      expect(fetchMock).toHaveBeenCalledTimes(2)
      expect(listener).toHaveBeenCalledTimes(1)
      unsubscribe()
      release()
    })

    it('does not notify a listener that left while a poll was in flight', async () => {
      let release = () => {}
      stubFetch({ 'GET /api/missions': () => new Promise<Response>((resolve) => (release = () => resolve(json([])))) })
      const listener = vi.fn()
      const unsubscribe = createHttpApi().subscribe(listener)
      await vi.advanceTimersByTimeAsync(POLL_MS)
      unsubscribe()
      release()
      await vi.advanceTimersByTimeAsync(0)
      expect(listener).not.toHaveBeenCalled()
    })

    it('notifies straight after a change it made itself', async () => {
      const { api } = pollable()
      const listener = vi.fn()
      const unsubscribe = api.subscribe(listener)
      await api.markDone('m1')
      expect(listener).toHaveBeenCalledTimes(1)
      unsubscribe()
    })

    it('notifies straight after asking for a report', async () => {
      const { api } = pollable()
      const listener = vi.fn()
      const unsubscribe = api.subscribe(listener)
      await api.generateReport('m1')
      expect(listener).toHaveBeenCalledTimes(1)
      unsubscribe()
    })

    it('notifies straight after asking for an explorer', async () => {
      const { api } = pollable()
      const listener = vi.fn()
      const unsubscribe = api.subscribe(listener)
      await api.buildExplorer('m1', 'Add a heatmap layer')
      expect(listener).toHaveBeenCalledTimes(1)
      unsubscribe()
    })

    it('does not notify after a change that was rejected', async () => {
      stubFetch({ 'POST /api/missions/m1/messages': () => json({ field: 'text', message: 'Write a reply' }, 422) })
      const api = createHttpApi()
      const listener = vi.fn()
      const unsubscribe = api.subscribe(listener)
      await api.sendMessage('m1', '').catch(() => {})
      expect(listener).not.toHaveBeenCalled()
      unsubscribe()
    })
  })
})
