import { ArrowUpRight } from 'lucide-react'
import { formatSynced, hostname } from '../format'
import type { Dataset } from '../types'

export function DatasetTable({ datasets }: { datasets: Dataset[] }) {
  return (
    <table className="w-full text-left text-sm whitespace-nowrap">
      <thead>
        <tr className="border-b border-line-soft text-xs text-muted [&>th]:pb-2.5 [&>th]:font-normal">
          <th>Name</th>
          <th>Source</th>
          <th className="hidden text-right sm:table-cell">Series</th>
          <th className="hidden pl-10 sm:table-cell">Range</th>
          <th className="hidden text-right sm:table-cell">Added</th>
        </tr>
      </thead>
      <tbody>
        {datasets.map((dataset) => (
          <tr key={dataset.id} className="border-b border-line-soft last:border-0 [&>td]:py-3.5">
            <td className="max-w-48 pr-4 font-medium whitespace-normal">{dataset.name}</td>
            <td className="max-sm:w-full max-sm:max-w-0 max-sm:truncate sm:pr-4">
              <a
                href={dataset.url}
                target="_blank"
                rel="noreferrer"
                className="group items-center gap-0.5 text-muted transition-colors duration-150 hover:text-ink sm:inline-flex"
              >
                {hostname(dataset.url)}
                <ArrowUpRight size={13} strokeWidth={1.75} aria-hidden="true" className="opacity-0 transition-opacity duration-150 group-hover:opacity-100 max-sm:hidden" />
              </a>
            </td>
            <td className="hidden text-right font-mono text-[13px] sm:table-cell">{dataset.seriesCount || '—'}</td>
            <td className="hidden pl-10 text-muted sm:table-cell">{dataset.dateRange || '—'}</td>
            <td className="hidden text-right text-muted sm:table-cell">{formatSynced(dataset.syncedAt)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
