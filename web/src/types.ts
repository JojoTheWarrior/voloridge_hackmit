export type MissionStatus = 'running' | 'done' | 'failed'
export type StepKey = 'plan' | 'pull' | 'test' | 'chart' | 'writeup'
export type StepState = 'pending' | 'active' | 'done'

export interface MissionStep {
  key: StepKey
  label: string
  state: StepState
}

export interface SeriesPoint {
  date: string
  a: number
  b: number
}

export interface MissionResult {
  seriesA: string
  seriesB: string
  points: SeriesPoint[]
  correlation: number
  bestLagDays: number
  pValue: number
  n: number
  note: string
  verdict: string
}

export interface Mission {
  id: string
  title: string
  hypothesis: string
  status: MissionStatus
  datasetIds: string[]
  createdAt: string
  elapsedSeconds: number
  steps: MissionStep[]
  result?: MissionResult
  error?: string
}

export interface Dataset {
  id: string
  name: string
  url: string
  seriesCount: number
  dateRange: string
  syncedAt: string
}
