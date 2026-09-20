import { LoaderCircle } from 'lucide-react'
import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import type { MissionSummary } from '../types'

export function MissionActionDialog({ mission, action, onSubmit, onClose }: {
  mission: MissionSummary
  action: 'rename' | 'delete'
  onSubmit: (title: string) => Promise<void>
  onClose: () => void
}) {
  const id = useId()
  const dialog = useRef<HTMLDialogElement>(null)
  const input = useRef<HTMLInputElement>(null)
  const locked = useRef(false)
  const [title, setTitle] = useState(mission.title)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const deleting = action === 'delete'

  useEffect(() => {
    dialog.current?.showModal()
    input.current?.select()
  }, [])

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (locked.current || (!deleting && !title.trim())) return
    locked.current = true
    setBusy(true)
    setError('')
    try {
      await onSubmit(title.trim())
      onClose()
    } catch {
      setError(`Could not ${action} this mission. Please try again.`)
    } finally {
      locked.current = false
      setBusy(false)
    }
  }

  return (
    <dialog ref={dialog} aria-labelledby={`${id}-heading`} onClose={onClose}
      onCancel={(event) => { if (locked.current) event.preventDefault() }}
      onClick={(event) => { if (event.target === dialog.current && !locked.current) onClose() }}
      className="fade-in m-auto w-[400px] max-w-[calc(100vw-2rem)] rounded-2xl border border-line bg-paper p-0 text-ink backdrop:bg-scrim">
      <form onSubmit={submit} className="flex flex-col gap-5 p-6">
        <div>
          <h2 id={`${id}-heading`} className="text-base font-medium tracking-tight">{deleting ? 'Delete mission?' : 'Rename mission'}</h2>
          {deleting && <p className="mt-2 text-[13px] leading-relaxed text-muted">“{mission.title}” will be removed from Kingdom. Its Devin session will remain available and may continue running. This cannot be undone here.</p>}
        </div>
        {!deleting && <div>
          <label htmlFor={`${id}-name`} className="text-[13px] text-muted">Mission name</label>
          <input ref={input} id={`${id}-name`} value={title} maxLength={80} autoFocus required disabled={busy}
            onChange={(event) => setTitle(event.target.value)}
            className="mt-1.5 w-full rounded-lg border border-line bg-transparent px-3 py-2 text-sm outline-none focus:border-ink" />
        </div>}
        {error && <p role="alert" className="text-[13px] text-muted">{error}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" disabled={busy} autoFocus={deleting} onClick={onClose}
            className="rounded-full px-4 py-1.5 text-[13px] text-muted hover:text-ink disabled:opacity-40">Cancel</button>
          <button type="submit" disabled={busy || (!deleting && !title.trim())}
            className="flex items-center gap-2 rounded-full bg-ink px-4 py-1.5 text-[13px] text-paper hover:bg-ink/85 disabled:opacity-40">
            {busy && <LoaderCircle size={13} className="animate-spin" aria-hidden="true" />}
            {deleting ? 'Delete mission' : 'Save name'}
          </button>
        </div>
      </form>
    </dialog>
  )
}
