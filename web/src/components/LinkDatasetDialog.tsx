import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { useApi } from '../api/context'
import { ValidationError } from '../api/index'

interface FieldProps {
  label: string
  value: string
  onChange: (value: string) => void
  error?: string
  placeholder?: string
  autoFocus?: boolean
}

function Field({ label, value, onChange, error, placeholder, autoFocus }: FieldProps) {
  const id = useId()
  return (
    <div>
      <label htmlFor={id} className="text-[13px]">
        {label}
      </label>
      <input
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        autoFocus={autoFocus}
        autoComplete="off"
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${id}-error` : undefined}
        className="mt-1.5 block w-full rounded-lg border border-line px-3 py-2 text-sm outline-none transition-colors duration-150 placeholder:text-faint focus:border-ink"
      />
      {error && (
        <p id={`${id}-error`} className="mt-1.5 text-[13px] text-ink">
          {error}
        </p>
      )}
    </div>
  )
}

/** Mounted only while open, so every open starts from an empty form. */
export function LinkDatasetDialog({ onClose }: { onClose: () => void }) {
  const api = useApi()
  const titleId = useId()
  const dialogRef = useRef<HTMLDialogElement>(null)
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [error, setError] = useState<ValidationError>()

  useEffect(() => {
    dialogRef.current?.showModal()
  }, [])

  async function submit(event: FormEvent) {
    event.preventDefault()
    try {
      await api.linkDataset({ name, url })
      onClose()
    } catch (caught) {
      if (!(caught instanceof ValidationError)) throw caught
      setError(caught)
    }
  }

  const edit = (set: (value: string) => void) => (value: string) => {
    set(value)
    setError(undefined)
  }

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      onClose={onClose}
      onClick={(event) => {
        if (event.target === dialogRef.current) onClose()
      }}
      className="fade-in m-auto w-[400px] max-w-[calc(100vw-2rem)] rounded-2xl border border-line bg-paper p-0 text-ink backdrop:bg-scrim"
    >
      <form onSubmit={submit} noValidate className="flex flex-col gap-4 p-6">
        <div>
          <h2 id={titleId} className="text-base font-medium tracking-tight">
            Link a dataset
          </h2>
          <p className="mt-1 text-[13px] text-muted">Point to where the data lives. Nothing is copied.</p>
        </div>
        <Field label="Name" value={name} onChange={edit(setName)} error={error?.field === 'name' ? error.message : undefined} placeholder="FRED oil prices" autoFocus />
        <Field label="URL" value={url} onChange={edit(setUrl)} error={error?.field === 'url' ? error.message : undefined} placeholder="https://" />
        <div className="mt-1 flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-full px-4 py-1.5 text-[13px] text-muted transition-colors duration-150 hover:text-ink">
            Cancel
          </button>
          <button type="submit" className="rounded-full bg-ink px-4 py-1.5 text-[13px] text-paper transition-colors duration-150 hover:bg-ink/85">
            Link dataset
          </button>
        </div>
      </form>
    </dialog>
  )
}
