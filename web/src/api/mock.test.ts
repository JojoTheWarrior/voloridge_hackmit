import { makeMission } from '../test/missions'
import type { Mission } from '../types'
import { ValidationError } from './index'
import { createMockApi } from './mock'
import { REPLY_BEAT, SCRIPT } from './script'

const STEP_MS = 1000

const kinds = (mission?: Mission) => mission?.events.map((e) => e.kind)

describe('mock api', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  const empty = { missions: [], datasets: [] }
  const seeded = (...missions: Mission[]) => createMockApi({ stepMs: STEP_MS, seed: { missions, datasets: [] } })

  it('lists seeded missions newest first, as summaries', async () => {
    const api = createMockApi()
    const missions = await api.listMissions()
    expect(missions.length).toBeGreaterThan(0)
    const times = missions.map((m) => Date.parse(m.createdAt))
    expect(times).toEqual([...times].sort((a, b) => b - a))
    expect(Object.keys(missions[0]).sort()).toEqual(['createdAt', 'hypothesis', 'id', 'status', 'title', 'updatedAt'])
  })

  it('seeds every status', async () => {
    const statuses = new Set((await createMockApi().listMissions()).map((m) => m.status))
    expect(statuses).toEqual(new Set(['working', 'waiting', 'done', 'failed']))
  })

  it('is not in demo mode unless asked', async () => {
    expect(await createMockApi().getMeta()).toEqual({ demo: false })
    expect(await createMockApi({ demo: true }).getMeta()).toEqual({ demo: true })
  })

  it('creates a working mission whose thread opens with the hypothesis', async () => {
    const api = createMockApi({ stepMs: STEP_MS, seed: empty })
    const mission = await api.createMission({ hypothesis: '  Does wind move PM2.5?  ', datasetIds: ['d1'], reference: 'private notes' })
    expect(mission.status).toBe('working')
    expect(mission.hypothesis).toBe('Does wind move PM2.5?')
    expect(mission.title).toBe('Does wind move PM2.5')
    expect(mission.datasetIds).toEqual(['d1'])
    expect(mission.updatedAt).toBe(mission.createdAt)
    expect(mission.events).toEqual([{ id: 'e1', at: mission.createdAt, kind: 'user_message', text: 'Does wind move PM2.5?' }])
    expect(JSON.stringify(mission)).not.toContain('private notes')
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

  it('plays the script one beat at a time, then waits with a conclusion', async () => {
    const api = createMockApi({ stepMs: STEP_MS, seed: empty })
    const { id } = await api.createMission({ hypothesis: 'A leads B', datasetIds: [] })
    for (let beat = 1; beat < SCRIPT.length; beat++) {
      vi.advanceTimersByTime(STEP_MS)
      const m = await api.getMission(id)
      expect(m?.status).toBe('working')
      expect(m?.events).toHaveLength(beat + 1)
    }
    vi.advanceTimersByTime(STEP_MS)
    const settled = await api.getMission(id)
    expect(settled?.status).toBe('waiting')
    expect(kinds(settled)).toEqual(['user_message', ...SCRIPT.map((b) => b.kind)])
    expect(settled?.events.some((e) => e.kind === 'step' && e.state === 'active')).toBe(false)
    expect(Date.parse(settled!.updatedAt)).toBeGreaterThan(Date.parse(settled!.createdAt))

    vi.advanceTimersByTime(STEP_MS * 3)
    expect(await api.getMission(id)).toEqual(settled)
    expect(vi.getTimerCount()).toBe(0)
  })

  it('gives the same findings for the same hypothesis', async () => {
    const api = createMockApi({ stepMs: STEP_MS, seed: empty })
    const a = await api.createMission({ hypothesis: 'A leads B', datasetIds: [] })
    const b = await api.createMission({ hypothesis: 'A leads B', datasetIds: [] })
    vi.advanceTimersByTime(STEP_MS * SCRIPT.length)
    const strip = (m?: Mission) => m?.events.map(({ at: _at, ...rest }) => rest)
    expect(strip(await api.getMission(a.id))).toEqual(strip(await api.getMission(b.id)))
    expect(a.id).not.toBe(b.id)
  })

  it('carries seeded working missions on from where their thread stops', async () => {
    const mission = makeMission('working')
    const api = seeded(mission, makeMission('waiting'), makeMission('done'), makeMission('failed'))
    expect(vi.getTimerCount()).toBe(1)
    vi.advanceTimersByTime(STEP_MS)
    expect((await api.getMission(mission.id))?.events).toHaveLength(mission.events.length + 1)
    vi.advanceTimersByTime(STEP_MS * SCRIPT.length)
    expect(kinds(await api.getMission(mission.id))).toEqual(['user_message', ...SCRIPT.map((b) => b.kind)])
    expect((await api.listMissions()).map((m) => m.status).sort()).toEqual(['done', 'failed', 'waiting', 'waiting'])
  })

  it('leaves a working mission alone once its script has been played out', async () => {
    const mission = makeMission('working', { events: makeMission('done').events })
    const api = seeded(mission)
    vi.advanceTimersByTime(STEP_MS * 3)
    expect(await api.getMission(mission.id)).toEqual(mission)
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

  describe('sendMessage', () => {
    it('appends the trimmed reply, goes back to work, then answers and waits', async () => {
      const mission = makeMission('waiting', { needsUser: 'Drop the outlier?' })
      const api = seeded(mission)
      const listener = vi.fn()
      api.subscribe(listener)

      await api.sendMessage(mission.id, '  Yes, drop it.  ')
      const working = await api.getMission(mission.id)
      expect(working?.status).toBe('working')
      expect(working?.needsUser).toBeUndefined()
      expect(working?.events.at(-1)).toMatchObject({ kind: 'user_message', text: 'Yes, drop it.' })
      expect(listener).toHaveBeenCalledTimes(1)

      vi.advanceTimersByTime(STEP_MS)
      const answered = await api.getMission(mission.id)
      expect(answered?.status).toBe('waiting')
      expect(answered?.events.at(-1)).toMatchObject(REPLY_BEAT)
      expect(answered?.events).toHaveLength(mission.events.length + 2)
      expect(new Set(answered?.events.map((e) => e.id)).size).toBe(answered?.events.length)
      expect(listener).toHaveBeenCalledTimes(2)
      expect(vi.getTimerCount()).toBe(0)
    })

    it('reopens a done mission', async () => {
      const mission = makeMission('done')
      const api = seeded(mission)
      await api.sendMessage(mission.id, 'One more thing')
      expect((await api.getMission(mission.id))?.status).toBe('working')
      vi.advanceTimersByTime(STEP_MS)
      expect((await api.getMission(mission.id))?.status).toBe('waiting')
    })

    it('answers after the script when sent mid-run', async () => {
      const mission = makeMission('working')
      const api = seeded(mission)
      await api.sendMessage(mission.id, 'Also check weekends')
      const beatsLeft = SCRIPT.length - (mission.events.length - 1)
      vi.advanceTimersByTime(STEP_MS * beatsLeft)
      const concluded = await api.getMission(mission.id)
      expect(concluded?.status).toBe('working')
      expect(concluded?.events.at(-1)?.kind).toBe('conclusion')
      vi.advanceTimersByTime(STEP_MS)
      const settled = await api.getMission(mission.id)
      expect(settled?.status).toBe('waiting')
      expect(settled?.events.at(-1)).toMatchObject(REPLY_BEAT)
      expect(settled?.events.filter((e) => e.kind === 'conclusion')).toHaveLength(1)
    })

    it.each(['', '   ', '\n'])('rejects blank text %j', async (text) => {
      const mission = makeMission('waiting')
      const api = seeded(mission)
      const error = await api.sendMessage(mission.id, text).catch((e) => e)
      expect(error).toBeInstanceOf(ValidationError)
      expect(error.field).toBe('text')
      expect(error.message).toBe('Write a reply')
      expect(await api.getMission(mission.id)).toEqual(mission)
    })

    it('rejects an unknown mission', async () => {
      await expect(seeded().sendMessage('nope', 'hello')).rejects.toThrow('Mission not found')
    })
  })

  describe('markDone', () => {
    it('marks a waiting mission done and notifies', async () => {
      const mission = makeMission('waiting', { needsUser: 'Drop the outlier?' })
      const api = seeded(mission)
      const listener = vi.fn()
      api.subscribe(listener)
      await api.markDone(mission.id)
      const done = await api.getMission(mission.id)
      expect(done?.status).toBe('done')
      expect(done?.needsUser).toBeUndefined()
      expect(done?.events).toEqual(mission.events)
      expect(listener).toHaveBeenCalledTimes(1)
    })

    it('stops a mission that is still working', async () => {
      const mission = makeMission('working')
      const api = seeded(mission)
      await api.markDone(mission.id)
      expect(vi.getTimerCount()).toBe(0)
      vi.advanceTimersByTime(STEP_MS * SCRIPT.length)
      const done = await api.getMission(mission.id)
      expect(done?.status).toBe('done')
      expect(done?.events).toEqual(mission.events)
    })

    it('clears a failed mission from the active list', async () => {
      const mission = makeMission('failed')
      const api = seeded(mission)
      await api.markDone(mission.id)
      expect((await api.getMission(mission.id))?.status).toBe('done')
    })

    it('is harmless on a mission that is already done', async () => {
      const mission = makeMission('done')
      const api = seeded(mission)
      await api.markDone(mission.id)
      expect((await api.getMission(mission.id))?.status).toBe('done')
    })

    it('rejects an unknown mission', async () => {
      await expect(seeded().markDone('nope')).rejects.toThrow('Mission not found')
    })
  })

  describe('generateReport', () => {
    const artifactIds = (mission?: Mission) => mission?.events.flatMap((e) => (e.kind === 'artifact' ? [e.artifact.id] : []))

    it('goes to work on the report without adding a message, then delivers it and waits', async () => {
      const mission = makeMission('waiting')
      const api = seeded(mission)
      const listener = vi.fn()
      api.subscribe(listener)

      await api.generateReport(mission.id)
      const pending = await api.getMission(mission.id)
      expect(pending).toMatchObject({ status: 'working', reportPending: true })
      expect(pending?.report).toBeUndefined()
      expect(pending?.events).toEqual(mission.events)
      expect(listener).toHaveBeenCalledTimes(1)

      vi.advanceTimersByTime(STEP_MS)
      const delivered = await api.getMission(mission.id)
      expect(delivered).toMatchObject({ status: 'waiting', reportPending: false })
      expect(delivered?.report?.headline).not.toBe('')
      expect(delivered?.events.at(-1)).toMatchObject({ id: 'report', kind: 'report', at: delivered?.report?.generatedAt })
      expect(delivered?.events.slice(0, -1)).toEqual(mission.events)
      expect(delivered?.updatedAt).toBe(delivered?.report?.generatedAt)
      expect(listener).toHaveBeenCalledTimes(2)
      expect(vi.getTimerCount()).toBe(0)
    })

    it('features artifacts that are in the thread', async () => {
      const mission = makeMission('waiting')
      const api = seeded(mission)
      await api.generateReport(mission.id)
      vi.advanceTimersByTime(STEP_MS)
      const delivered = await api.getMission(mission.id)
      expect(delivered?.report?.keyArtifactIds.length).toBeGreaterThan(0)
      delivered?.report?.keyArtifactIds.forEach((id) => expect(artifactIds(delivered)).toContain(id))
    })

    it('returns a done mission to done', async () => {
      const mission = makeMission('done')
      const api = seeded(mission)
      await api.generateReport(mission.id)
      expect((await api.getMission(mission.id))?.status).toBe('working')
      vi.advanceTimersByTime(STEP_MS)
      expect(await api.getMission(mission.id)).toMatchObject({ status: 'done', reportPending: false })
    })

    it('leaves a done mission open if you reply while the report is being written', async () => {
      const mission = makeMission('done')
      const api = seeded(mission)
      await api.generateReport(mission.id)
      await api.sendMessage(mission.id, 'One more thing')
      vi.advanceTimersByTime(STEP_MS * 2)
      const settled = await api.getMission(mission.id)
      expect(settled).toMatchObject({ status: 'waiting', reportPending: false })
      expect(kinds(settled)?.slice(-3)).toEqual(['user_message', 'report', 'thought'])
    })

    it('does nothing when asked again while one is pending', async () => {
      const mission = makeMission('waiting')
      const api = seeded(mission)
      const listener = vi.fn()
      api.subscribe(listener)
      await api.generateReport(mission.id)
      await api.generateReport(mission.id)
      expect(listener).toHaveBeenCalledTimes(1)
      expect(vi.getTimerCount()).toBe(1)
      vi.advanceTimersByTime(STEP_MS)
      expect((await api.getMission(mission.id))?.events.filter((e) => e.kind === 'report')).toHaveLength(1)
      vi.advanceTimersByTime(STEP_MS * 3)
      expect(await api.getMission(mission.id)).toMatchObject({ status: 'waiting', reportPending: false })
    })

    it('rewrites the report on request, moving the one report event to the end', async () => {
      const mission = makeMission('waiting')
      const api = seeded(mission)
      await api.generateReport(mission.id)
      vi.advanceTimersByTime(STEP_MS)
      const first = (await api.getMission(mission.id))!.report!
      await api.sendMessage(mission.id, 'And weekends?')
      vi.advanceTimersByTime(STEP_MS)

      await api.generateReport(mission.id)
      const pending = await api.getMission(mission.id)
      expect(pending?.report).toEqual(first)
      expect(pending?.reportPending).toBe(true)
      vi.advanceTimersByTime(STEP_MS)

      const rewritten = await api.getMission(mission.id)
      expect(rewritten?.report?.summary).not.toBe(first.summary)
      expect(Date.parse(rewritten!.report!.generatedAt)).toBeGreaterThan(Date.parse(first.generatedAt))
      expect(kinds(rewritten)?.filter((k) => k === 'report')).toHaveLength(1)
      expect(rewritten?.events.at(-1)?.kind).toBe('report')
      expect(new Set(rewritten?.events.map((e) => e.id)).size).toBe(rewritten?.events.length)
    })

    it('delivers after the script when asked mid-run', async () => {
      const mission = makeMission('working')
      const api = seeded(mission)
      await api.generateReport(mission.id)
      const beatsLeft = SCRIPT.length - (mission.events.length - 1)
      vi.advanceTimersByTime(STEP_MS * beatsLeft)
      expect(await api.getMission(mission.id)).toMatchObject({ status: 'working', reportPending: true })
      vi.advanceTimersByTime(STEP_MS)
      const settled = await api.getMission(mission.id)
      expect(settled).toMatchObject({ status: 'waiting', reportPending: false })
      expect(kinds(settled)?.slice(-2)).toEqual(['conclusion', 'report'])
    })

    it('is dropped when the mission is marked done first', async () => {
      const mission = makeMission('waiting')
      const api = seeded(mission)
      await api.generateReport(mission.id)
      await api.markDone(mission.id)
      vi.advanceTimersByTime(STEP_MS * 2)
      const done = await api.getMission(mission.id)
      expect(done).toMatchObject({ status: 'done', reportPending: false })
      expect(done?.report).toBeUndefined()
      expect(vi.getTimerCount()).toBe(0)
    })

    it('does not mistake a delivered report for a played beat when carrying a seeded mission on', async () => {
      const played = makeMission('working')
      const mission = { ...played, events: [...played.events, { id: 'report', at: played.updatedAt, kind: 'report' as const }] }
      const api = seeded(mission)
      vi.advanceTimersByTime(STEP_MS * SCRIPT.length)
      expect(kinds(await api.getMission(mission.id))?.filter((k) => k !== 'report')).toEqual(['user_message', ...SCRIPT.map((b) => b.kind)])
    })

    it('rejects an unknown mission', async () => {
      await expect(seeded().generateReport('nope')).rejects.toThrow('Mission not found')
    })
  })

  it('creates missions with no report pending', async () => {
    const mission = await createMockApi({ seed: empty }).createMission({ hypothesis: 'A leads B', datasetIds: [] })
    expect(mission.reportPending).toBe(false)
    expect(mission.report).toBeUndefined()
  })

  it.each(['', '   ', '\n\t'])('rejects blank hypothesis %j', async (hypothesis) => {
    const api = createMockApi({ seed: empty })
    const error = await api.createMission({ hypothesis, datasetIds: [] }).catch((e) => e)
    expect(error).toBeInstanceOf(ValidationError)
    expect(error.field).toBe('hypothesis')
    expect(error.message).toBe('Describe a connection to test')
    expect(await api.listMissions()).toHaveLength(0)
  })

  it('resolves undefined for an unknown mission', async () => {
    expect(await createMockApi().getMission('nope')).toBeUndefined()
  })

  it('returns copies, not store references', async () => {
    const api = createMockApi()
    const [first] = await api.listMissions()
    first.title = 'mutated'
    const mission = await api.getMission(first.id)
    mission!.events.length = 0
    const again = await api.getMission(first.id)
    expect(again?.title).not.toBe('mutated')
    expect(again?.events.length).toBeGreaterThan(0)
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
      expect(dataset.kind).toBe('other')
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
