import type { Dataset } from '../types'

interface DatasetChipsProps {
  datasets: Dataset[]
  selected: Set<string>
  onToggle: (id: string) => void
}

export function DatasetChips({ datasets, selected, onToggle }: DatasetChipsProps) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {datasets.map((dataset) => {
        const pressed = selected.has(dataset.id)
        return (
          <button
            key={dataset.id}
            type="button"
            aria-pressed={pressed}
            onClick={() => onToggle(dataset.id)}
            className={`rounded-full border px-2.5 py-1 text-xs transition-colors duration-150 ${
              pressed ? 'border-line text-ink hover:border-faint' : 'border-line-soft text-faint hover:text-muted'
            }`}
          >
            {dataset.name}
          </button>
        )
      })}
    </div>
  )
}
