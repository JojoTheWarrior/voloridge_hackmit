import type { StatsArtifact as StatsSpec } from '../../types'
import { EmptyBody } from './EmptyBody'
import { asText } from './text'

const COLUMNS: Record<number, string> = { 1: 'sm:grid-cols-2', 2: 'sm:grid-cols-2', 3: 'sm:grid-cols-3', 4: 'sm:grid-cols-4' }

export function StatsArtifact({ artifact }: { artifact: StatsSpec }) {
  const items = (Array.isArray(artifact.items) ? artifact.items : [])
    .filter((item) => item !== null && typeof item === 'object')
    .map((item) => ({ label: asText(item.label), value: asText(item.value) || '—' }))
  if (items.length === 0) return <EmptyBody />

  return (
    <dl className={`grid grid-cols-2 gap-x-6 gap-y-4 ${COLUMNS[items.length] ?? 'sm:grid-cols-3'}`}>
      {items.map((item, index) => (
        <div key={index} className="min-w-0">
          <dt className="truncate text-xs text-muted" title={item.label}>
            {item.label}
          </dt>
          <dd className="mt-0.5 truncate font-mono text-lg tracking-tight" title={item.value}>
            {item.value}
          </dd>
        </div>
      ))}
    </dl>
  )
}
