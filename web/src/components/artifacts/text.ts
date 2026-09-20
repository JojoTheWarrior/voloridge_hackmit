/** Artifact specs come from a model, so fields typed as strings can arrive as anything. */
export const asText = (value: unknown): string =>
  typeof value === 'string' ? value : typeof value === 'number' || typeof value === 'boolean' ? String(value) : ''

export const truncate = (value: string, max: number) => (value.length > max ? `${value.slice(0, max).trimEnd()}…` : value)
