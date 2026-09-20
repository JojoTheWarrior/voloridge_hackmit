import { LayoutGrid, LayoutList } from 'lucide-react'
import type { DatasetView } from '../hooks/useDatasetView'

const OPTIONS = [
  { view: 'list', label: 'List view', Icon: LayoutList },
  { view: 'card', label: 'Card view', Icon: LayoutGrid },
] as const

export function ViewToggle({ view, onChange }: { view: DatasetView; onChange: (view: DatasetView) => void }) {
  return (
    <div role="group" aria-label="View" className="flex gap-0.5 rounded-lg border border-line p-0.5">
      {OPTIONS.map(({ view: option, label, Icon }) => (
        <button
          key={option}
          type="button"
          aria-label={label}
          aria-pressed={view === option}
          onClick={() => onChange(option)}
          className={`rounded-md p-1.5 transition-colors duration-150 ${view === option ? 'bg-fill text-ink' : 'text-muted hover:text-ink'}`}
        >
          <Icon size={14} strokeWidth={1.75} aria-hidden="true" />
        </button>
      ))}
    </div>
  )
}
