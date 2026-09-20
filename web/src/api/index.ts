import type { Dataset, Meta, Mission, MissionSummary, ResearchFinding } from '../types'

export interface Api {
  getMeta(): Promise<Meta>
  /** Newest first. */
  listMissions(): Promise<MissionSummary[]>
  getMission(id: string): Promise<Mission | undefined>
  /** `reference` is prior research for Devin to retrace; it is never shown in the thread. */
  createMission(input: { hypothesis: string; datasetIds: string[]; reference?: string }): Promise<Mission>
  /** Replying to a done mission reopens it. */
  sendMessage(id: string, text: string): Promise<void>
  markDone(id: string): Promise<void>
  updateMission(id: string, input: { title?: string; pinned?: boolean }): Promise<void>
  deleteMission(id: string): Promise<void>
  /** Asks Devin to compile the mission's report; a second request while one is pending does nothing. */
  generateReport(id: string): Promise<void>
  /** Asks Devin to build, or with `instructions` to change, the mission's explorer. No-op while one is pending. */
  buildExplorer(id: string, instructions?: string): Promise<void>
  listDatasets(): Promise<Dataset[]>
  listResearch(): Promise<ResearchFinding[]>
  linkDataset(input: { name: string; url: string }): Promise<Dataset>
  /** Calls `listener` after any change; returns an unsubscribe function. */
  subscribe(listener: () => void): () => void
}

export type ValidationField = 'name' | 'url' | 'hypothesis' | 'text' | 'reference' | 'title' | 'pinned'

export class ValidationError extends Error {
  field: ValidationField

  constructor(field: ValidationField, message: string) {
    super(message)
    this.name = 'ValidationError'
    this.field = field
  }
}
