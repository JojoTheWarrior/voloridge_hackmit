import type { Dataset, Mission } from '../types'

export interface Api {
  /** Newest first. */
  listMissions(): Promise<Mission[]>
  getMission(id: string): Promise<Mission | undefined>
  createMission(input: { hypothesis: string; datasetIds: string[] }): Promise<Mission>
  listDatasets(): Promise<Dataset[]>
  linkDataset(input: { name: string; url: string }): Promise<Dataset>
  /** Calls `listener` after any change; returns an unsubscribe function. */
  subscribe(listener: () => void): () => void
}

export type ValidationField = 'name' | 'url' | 'hypothesis'

export class ValidationError extends Error {
  field: ValidationField

  constructor(field: ValidationField, message: string) {
    super(message)
    this.name = 'ValidationError'
    this.field = field
  }
}
