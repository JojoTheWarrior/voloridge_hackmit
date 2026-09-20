import { ArrowUp } from 'lucide-react'
import { useLayoutEffect, useState, type KeyboardEvent, type Ref } from 'react'
import type { Dataset } from '../types'
import { DatasetChips } from './DatasetChips'

const MAX_HEIGHT = 240

interface ComposerProps {
  datasets: Dataset[]
  value: string
  onChange: (value: string) => void
  onSubmit: (hypothesis: string, datasetIds: string[]) => void
  inputRef: Ref<HTMLTextAreaElement>
}

export function Composer({ datasets, value, onChange, onSubmit, inputRef }: ComposerProps) {
  // Tracking what is switched off keeps newly linked datasets on by default.
  const [deselected, setDeselected] = useState<Set<string>>(new Set())
  const [textarea, setTextarea] = useState<HTMLTextAreaElement | null>(null)
  const selected = new Set(datasets.filter((d) => !deselected.has(d.id)).map((d) => d.id))
  const empty = value.trim() === ''

  useLayoutEffect(() => {
    if (!textarea) return
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight, MAX_HEIGHT)}px`
  }, [textarea, value])

  function toggle(id: string) {
    setDeselected((current) => {
      const next = new Set(current)
      if (!next.delete(id)) next.add(id)
      return next
    })
  }

  function submit() {
    if (!empty) onSubmit(value, [...selected])
  }

  function onKeyDown(event: KeyboardEvent) {
    if (event.key !== 'Enter' || event.shiftKey || event.nativeEvent.isComposing) return
    event.preventDefault()
    submit()
  }

  return (
    <div className="rounded-2xl border border-line bg-white p-3 transition-colors duration-150 focus-within:border-ink">
      <textarea
        ref={(node) => {
          setTextarea(node)
          if (typeof inputRef === 'function') inputRef(node)
          else if (inputRef) inputRef.current = node
        }}
        aria-label="Mission prompt"
        autoFocus
        rows={2}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Describe a connection to test"
        className="block w-full resize-none bg-transparent px-1.5 pt-1 text-[15px] leading-relaxed outline-none placeholder:text-muted"
      />
      <div className="mt-2 flex items-end justify-between gap-3">
        <DatasetChips datasets={datasets} selected={selected} onToggle={toggle} />
        <button
          type="button"
          aria-label="Start mission"
          aria-disabled={empty}
          onClick={submit}
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-white transition-colors duration-150 ${
            empty ? 'cursor-default bg-line' : 'bg-ink hover:bg-ink/85'
          }`}
        >
          <ArrowUp size={16} strokeWidth={2} aria-hidden="true" />
        </button>
      </div>
    </div>
  )
}
