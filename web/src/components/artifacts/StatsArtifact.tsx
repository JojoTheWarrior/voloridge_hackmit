import type { StatsArtifact as StatsSpec } from '../../types'
import { EmptyBody } from './EmptyBody'
import { StatGrid } from './StatGrid'
import { asText } from './text'

export function StatsArtifact({ artifact }: { artifact: StatsSpec }) {
  const items = (Array.isArray(artifact.items) ? artifact.items : [])
    .filter((item) => item !== null && typeof item === 'object')
    .map((item) => ({ label: asText(item.label), value: asText(item.value) || '—' }))
  return items.length === 0 ? <EmptyBody /> : <StatGrid items={items} />
}
