import { Upload, X } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'

export interface ContextAttachment { title: string; text: string }
const MAX_CHARS = 100_000
const MAX_BYTES = 400_000

export function ContextDialog({ initial, onApply, onClose }: {
  initial?: ContextAttachment
  onApply: (attachment: ContextAttachment) => void
  onClose: () => void
}) {
  const titleId = useId()
  const dialog = useRef<HTMLDialogElement>(null)
  const reader = useRef<FileReader | null>(null)
  const [title, setTitle] = useState(initial?.title ?? 'Context notes')
  const [text, setText] = useState(initial?.text ?? '')
  const [error, setError] = useState('')
  const [reading, setReading] = useState(false)
  useEffect(() => {
    dialog.current?.showModal()
    return () => reader.current?.abort()
  }, [])

  function loadFile(file?: File) {
    if (!file) return
    setError('')
    if (!/\.(txt|md)$/i.test(file.name)) {
      setError('Choose a .txt or .md text file.')
      return
    }
    if (file.size > MAX_BYTES) {
      setError('Choose a text file under 400 KB and 100,000 characters.')
      return
    }
    const next = new FileReader()
    reader.current = next
    setReading(true)
    next.onload = () => {
      setReading(false)
      const content = typeof next.result === 'string' ? next.result : ''
      if (content.includes('\0') || !content.trim()) {
        setError('Choose a non-empty text file.')
      } else if (content.trim().length > MAX_CHARS) {
        setError('Keep context under 100,000 characters.')
      } else {
        setTitle(file.name)
        setText(content)
      }
    }
    next.onerror = () => { setReading(false); setError('Couldn’t read this file. Try again or paste its text below.') }
    next.readAsText(file)
  }

  const tooLong = text.trim().length > MAX_CHARS
  return (
    <dialog ref={dialog} aria-labelledby={titleId} onClose={onClose}
      onClick={(event) => { if (event.target === dialog.current) onClose() }}
      className="fade-in m-auto w-[620px] max-w-[calc(100vw-2rem)] rounded-2xl border border-line bg-paper p-0 text-ink backdrop:bg-scrim">
      <div className="flex max-h-[80dvh] flex-col overflow-y-auto">
        <div className="flex items-start justify-between gap-4 px-6 pt-6">
          <div>
            <h2 id={titleId} className="text-lg font-medium tracking-tight">Attach context</h2>
            <p className="mt-1 text-[13px] leading-relaxed text-muted">Upload a text file or paste background for this mission.</p>
          </div>
          <button type="button" aria-label="Close context" onClick={onClose} className="rounded-full p-1.5 text-muted hover:bg-fill hover:text-ink"><X size={16} /></button>
        </div>
        <form className="flex flex-col gap-3 p-6" onSubmit={(event) => {
          event.preventDefault()
          if (text.trim() && !tooLong && !reading) onApply({ title, text: text.trim() })
        }}>
          <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-line px-4 py-3 text-sm hover:bg-fill">
            <Upload size={16} aria-hidden="true" /> Choose text file <span className="text-xs text-muted">.txt or .md</span>
            <input aria-label="Choose text file" type="file" accept=".txt,.md,text/plain,text/markdown" disabled={reading}
              className="sr-only" onChange={(event) => { loadFile(event.target.files?.[0]); event.target.value = '' }} />
          </label>
          {reading && <p role="status" className="text-xs text-muted">Reading file…</p>}
          <label htmlFor={`${titleId}-notes`} className="text-[13px]">Context</label>
          <textarea id={`${titleId}-notes`} autoFocus rows={9} value={text} disabled={reading}
            onChange={(event) => { setText(event.target.value); setError('') }} aria-invalid={tooLong}
            placeholder="Paste notes, research, source links, or other background…"
            className="min-h-32 resize-y rounded-xl border border-line bg-transparent p-3 text-sm leading-relaxed outline-none placeholder:text-muted focus:border-ink" />
          {(error || tooLong) && <p role="alert" className="text-[13px]">{tooLong ? 'Keep context under 100,000 characters.' : error}</p>}
          <div className="flex items-center justify-between gap-3">
            <span className="text-xs text-muted">Sent with your mission when you start it.</span>
            <button disabled={!text.trim() || tooLong || reading} type="submit" className="rounded-full bg-ink px-4 py-2 text-[13px] text-paper disabled:opacity-40">Attach context</button>
          </div>
        </form>
      </div>
    </dialog>
  )
}
