import { ArrowUpRight } from 'lucide-react'
import { formatSynced } from '../format'
import type { Dataset } from '../types'

const hostname = (url: string) => new URL(url).hostname.replace(/^www\./, '')

export function DatasetTable({ datasets }: { datasets: Dataset[] }) {
  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-line-soft text-xs text-muted [&>th]:pb-2.5 [&>th]:font-normal">
          <th>Name</th>
          <th>Source</th>
          <th className="hidden text-right sm:table-cell">Series</th>
          <th className="hidden pl-10 sm:table-cell">Range</th>
          <th className="text-right">Synced</th>
        </tr>
      </thead>
      <tbody>
        {datasets.map((dataset) => (
          <tr key={dataset.id} className="border-b border-line-soft last:border-0 [&>td]:py-3.5">
            <td className="pr-4 font-medium">{dataset.name}</td>
            <td className="pr-4">
              <a
                href={dataset.url}
                target="_blank"
                rel="noreferrer"
                className="group inline-flex items-center gap-0.5 text-muted transition-colors duration-150 hover:text-ink"
              >
                {hostname(dataset.url)}
                <ArrowUpRight size={13} strokeWidth={1.75} aria-hidden="true" className="opacity-0 transition-opacity duration-150 group-hover:opacity-100" />
              </a>
            </td>
            <td className="hidden text-right font-mono text-[13px] sm:table-cell">{dataset.seriesCount}</td>
            <td className="hidden pl-10 text-muted sm:table-cell">{dataset.dateRange || '—'}</td>
            <td className="text-right text-muted">{formatSynced(dataset.syncedAt)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
