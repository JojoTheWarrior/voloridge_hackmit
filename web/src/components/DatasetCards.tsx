import { ArrowUpRight } from 'lucide-react'
import { formatSynced, hostname } from '../format'
import type { Dataset } from '../types'
import { DatasetThumbnail } from './DatasetThumbnail'

export function DatasetCards({ datasets }: { datasets: Dataset[] }) {
  return (
    <ul aria-label="Datasets" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {datasets.map((dataset) => (
        <li key={dataset.id} className="min-w-0 overflow-hidden rounded-xl border border-line bg-white">
          <DatasetThumbnail id={dataset.id} kind={dataset.kind} />
          <div className="p-4">
            <h2 className="truncate text-sm font-medium">{dataset.name}</h2>
            <a
              href={dataset.url}
              target="_blank"
              rel="noreferrer"
              className="group mt-0.5 flex items-center gap-0.5 text-[13px] text-muted transition-colors duration-150 hover:text-ink"
            >
              <span className="truncate">{hostname(dataset.url)}</span>
              <ArrowUpRight size={13} strokeWidth={1.75} aria-hidden="true" className="shrink-0 opacity-0 transition-opacity duration-150 group-hover:opacity-100" />
            </a>
            <p className="mt-3 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-muted">
              <span>
                <span className="font-mono">{dataset.seriesCount}</span> series
              </span>
              <span>{dataset.dateRange || '—'}</span>
              <span>synced {formatSynced(dataset.syncedAt)}</span>
            </p>
          </div>
        </li>
      ))}
    </ul>
  )
}
