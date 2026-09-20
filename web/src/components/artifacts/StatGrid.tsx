import type { Stat } from '../../types'

// A stat is meant to be one number; anything longer is set small so it can be read in full.
const LARGE_MAX = 16

const COLUMNS: Record<number, string> = { 1: 'sm:grid-cols-2', 2: 'sm:grid-cols-2', 3: 'sm:grid-cols-3', 4: 'sm:grid-cols-4' }

/** Label-over-value grid, shared by stats artifacts and a mission's conclusion. */
export function StatGrid({ items }: { items: Stat[] }) {
  return (
    <dl className={`grid grid-cols-2 gap-x-6 gap-y-4 ${COLUMNS[items.length] ?? 'sm:grid-cols-3'}`}>
      {items.map((item, index) => (
        <div key={index} className="min-w-0">
          <dt className="truncate text-xs text-muted" title={item.label}>
            {item.label}
          </dt>
          <dd
            className={`mt-0.5 font-mono tracking-tight ${
              item.value.length > LARGE_MAX ? 'line-clamp-3 text-[13px] leading-snug break-words' : 'truncate text-lg'
            }`}
            title={item.value}
          >
            {item.value}
          </dd>
        </div>
      ))}
    </dl>
  )
}
