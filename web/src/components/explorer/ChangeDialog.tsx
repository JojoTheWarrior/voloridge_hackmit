import { useEffect, useId, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { INSTRUCTIONS_MAX } from '../../api/explorer'
import { ValidationError } from '../../api/index'

// The counter stays out of the way until the limit is worth knowing about.
const COUNTER_FROM = INSTRUCTIONS_MAX * 0.9

interface ChangeDialogProps {
  /** Rejects with a `ValidationError` when the server objects to the text. */
  onSubmit: (instructions: string) => Promise<void>
  onClose: () => void
}

/** Mounted only while open, so every open starts from an empty form. */
export function ChangeDialog({ onSubmit, onClose }: ChangeDialogProps) {
  const id = useId()
  const dialogRef = useRef<HTMLDialogElement>(null)
  const [value, setValue] = useState('')
  const [problem, setProblem] = useState<string>()
  const [sending, setSending] = useState(false)
  // State lags a render behind; the ref is what stops a second submit in the same tick.
  const locked = useRef(false)
  const text = value.trim()
  const over = text.length > INSTRUCTIONS_MAX

  useEffect(() => {
    dialogRef.current?.showModal()
  }, [])

  async function submit(event?: FormEvent) {
    event?.preventDefault()
    if (over || locked.current) return
    locked.current = true
    setSending(true)
    try {
      await onSubmit(text)
      onClose()
    } catch (caught) {
      setProblem(caught instanceof ValidationError ? caught.message : 'That did not send. Try again.')
    } finally {
      locked.current = false
      setSending(false)
    }
  }

  function onKeyDown(event: KeyboardEvent) {
    if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) submit()
  }

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={`${id}-title`}
      onClose={onClose}
      onClick={(event) => {
        if (event.target === dialogRef.current) onClose()
      }}
      className="fade-in m-auto w-[440px] max-w-[calc(100vw-2rem)] rounded-2xl border border-line bg-paper p-0 text-ink backdrop:bg-scrim"
    >
      <form onSubmit={submit} noValidate className="flex flex-col gap-4 p-6">
        <div>
          <h2 id={`${id}-title`} className="text-base font-medium tracking-tight">
            Request a change
          </h2>
          <p className="mt-1 text-[13px] text-muted">Devin builds a new version with your change. Leave it empty to rebuild it as it is.</p>
        </div>
        <div>
          <div className="flex items-baseline justify-between gap-4">
            <label htmlFor={`${id}-text`} className="text-[13px]">
              What should change?
            </label>
            {text.length >= COUNTER_FROM && (
              <span className={`font-mono text-xs ${over ? 'text-ink' : 'text-muted'}`}>
                {text.length.toLocaleString('en-US')} / {INSTRUCTIONS_MAX.toLocaleString('en-US')}
              </span>
            )}
          </div>
          <textarea
            id={`${id}-text`}
            rows={4}
            value={value}
            onChange={(event) => {
              setValue(event.target.value)
              setProblem(undefined)
            }}
            onKeyDown={onKeyDown}
            placeholder="Add a heatmap layer"
            autoFocus
            aria-invalid={Boolean(problem)}
            aria-describedby={problem ? `${id}-problem` : undefined}
            className="mt-1.5 block max-h-64 min-h-24 w-full resize-none rounded-lg border border-line bg-transparent px-3 py-2 text-sm leading-relaxed outline-none transition-colors duration-150 field-sizing-content placeholder:text-faint focus:border-ink"
          />
          {problem && (
            <p id={`${id}-problem`} className="mt-1.5 text-[13px] text-ink">
              {problem}
            </p>
          )}
        </div>
        <div className="mt-1 flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-full px-4 py-1.5 text-[13px] text-muted transition-colors duration-150 hover:text-ink">
            Cancel
          </button>
          <button
            type="submit"
            aria-disabled={over || sending}
            className={`rounded-full bg-ink px-4 py-1.5 text-[13px] text-paper transition-colors duration-150 ${over || sending ? 'cursor-default opacity-40' : 'hover:bg-ink/85'}`}
          >
            Send to Devin
          </button>
        </div>
      </form>
    </dialog>
  )
}
