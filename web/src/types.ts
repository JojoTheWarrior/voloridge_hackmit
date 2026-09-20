export type MissionStatus = 'working' | 'waiting' | 'done' | 'failed'
export type StepState = 'active' | 'done'
export type DatasetKind = 'events' | 'markets' | 'weather' | 'air' | 'other'

export interface Stat {
  label: string
  value: string
}

interface ArtifactBase {
  id: string
  title: string
  caption?: string
}

export interface ChartSeries {
  name: string
  /** x is a number, or a string for dates and categories. */
  points: [number | string, number][]
}

export interface ChartArtifact extends ArtifactBase {
  type: 'chart'
  kind: 'line' | 'scatter' | 'bar'
  xLabel?: string
  yLabel?: string
  series: ChartSeries[]
  /** Short stat shown beside the title, e.g. "r = 0.58". */
  headline?: string
}

export interface ImagesArtifact extends ArtifactBase {
  type: 'images'
  items: { src: string; caption?: string }[]
}

export interface RelationArtifact extends ArtifactBase {
  type: 'relation'
  nodes: { id: string; label: string }[]
  edges: { from: string; to: string; label?: string }[]
}

export interface TableArtifact extends ArtifactBase {
  type: 'table'
  columns: string[]
  rows: string[][]
}

export interface StatsArtifact extends ArtifactBase {
  type: 'stats'
  items: Stat[]
}

export interface ImageArtifact extends ArtifactBase {
  type: 'image'
  src: string
}

export type Artifact =
  | ChartArtifact
  | ImagesArtifact
  | RelationArtifact
  | TableArtifact
  | StatsArtifact
  | ImageArtifact

interface EventBase {
  id: string
  at: string
}

export type MissionEvent = EventBase &
  (
    | { kind: 'user_message'; text: string }
    | { kind: 'thought'; text: string }
    | { kind: 'step'; stepId: string; label: string; state: StepState }
    | { kind: 'artifact'; artifact: Artifact }
    | { kind: 'conclusion'; verdict: string; summary: string; stats: Stat[] }
    | { kind: 'error'; text: string }
    /** Marks where in the thread a final report was delivered; the report itself is `Mission.report`. */
    | { kind: 'report' }
    /** Marks where an explorer build was delivered; the explorer itself is `Mission.explorer`. */
    | { kind: 'explorer' }
  )

export interface ReportStep {
  label: string
  /** One line: what this step established. */
  takeaway: string
}

/** Devin's look back over a whole mission: the thing a mission is shared as. */
export interface Report {
  /** The finding itself, not the question. */
  headline: string
  /** One paragraph. */
  summary: string
  stats: Stat[]
  /** Ids of artifacts already in the thread, in the order to feature them. */
  keyArtifactIds: string[]
  steps: ReportStep[]
  caveats: string[]
  nextQuestions: string[]
  generatedAt: string
}

/** A small interactive site Devin built for one mission, shown in a sandboxed frame. */
export interface Explorer {
  /** Goes up with every build; it is part of `src`, so a rebuild is never served from cache. */
  version: number
  title: string
  /** One or two sentences on what can be explored and how. */
  description: string
  /** Ready-to-use URL of the entry document, e.g. `/api/missions/m_1/explorer/2/index.html`. */
  src: string
  builtAt: string
}

export interface MissionSummary {
  id: string
  title: string
  hypothesis: string
  status: MissionStatus
  createdAt: string
  updatedAt: string
}

export interface Mission extends MissionSummary {
  datasetIds: string[]
  /** Link to the live Devin session; absent in demo mode or if creation failed. */
  sessionUrl?: string
  /** Set while Devin is waiting on a decision from the user. */
  needsUser?: string
  report?: Report
  /** True from the moment a report is requested until it arrives or the request fails. */
  reportPending: boolean
  explorer?: Explorer
  /** True from the moment a build is requested until it arrives or fails. A previous build stays usable meanwhile. */
  explorerPending: boolean
  events: MissionEvent[]
}

export interface Dataset {
  id: string
  name: string
  url: string
  kind: DatasetKind
  seriesCount: number
  dateRange: string
  syncedAt: string
}

export interface Meta {
  /** True when the server is running its scripted fake instead of real Devin. */
  demo: boolean
}
