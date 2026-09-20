import { ArrowUpRight, Search, X } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { useApi } from '../api/context'
import type { ResearchFinding } from '../types'

export interface ResearchAttachment { title: string; text: string }
const MAX_CHARS = 100_000

export function ResearchDialog({ initial, onApply, onClose }: {
  initial?: ResearchAttachment
  onApply: (attachment: ResearchAttachment) => void
  onClose: () => void
}) {
  const api = useApi()
  const titleId = useId()
  const dialog = useRef<HTMLDialogElement>(null)
  const searchInput = useRef<HTMLInputElement>(null)
  const notesInput = useRef<HTMLTextAreaElement>(null)
  const [mode, setMode] = useState<'library' | 'paste'>(initial ? 'paste' : 'library')
  const [findings, setFindings] = useState<ResearchFinding[]>()
  const [error, setError] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const [query, setQuery] = useState('')
  const [text, setText] = useState(initial?.text ?? '')

  useEffect(() => { dialog.current?.showModal() }, [])
  useEffect(() => { (mode === 'library' ? searchInput.current : notesInput.current)?.focus() }, [mode])
  useEffect(() => {
    let active = true
    api.listResearch().then(
      (rows) => { if (active) { setFindings(rows); setError(false) } },
      () => { if (active) setError(true) },
    )
    return () => { active = false }
  }, [api, attempt])

  const matches = findings?.filter((finding) =>
    `${finding.title} ${finding.summary} ${finding.source}`.toLowerCase().includes(query.trim().toLowerCase()),
  )
  const tooLong = text.trim().length > MAX_CHARS

  return (
    <dialog ref={dialog} aria-labelledby={titleId} onClose={onClose}
      onClick={(event) => { if (event.target === dialog.current) onClose() }}
      className="fade-in m-auto w-[620px] max-w-[calc(100vw-2rem)] rounded-2xl border border-line bg-paper p-0 text-ink backdrop:bg-scrim">
      <div className="flex max-h-[80dvh] flex-col">
        <div className="flex items-start justify-between gap-4 px-6 pt-6">
          <div>
            <h2 id={titleId} className="text-lg font-medium tracking-tight">Start from research</h2>
            <p className="mt-1 text-[13px] leading-relaxed text-muted">Give Devin a starting point. It will check the evidence and run its own analysis.</p>
          </div>
          <button type="button" aria-label="Close research" onClick={onClose} className="rounded-full p-1.5 text-muted hover:bg-fill hover:text-ink"><X size={16} /></button>
        </div>
        <div className="mt-5 flex gap-1 border-b border-line-soft px-6 pb-3" role="group" aria-label="Research source">
          {(['library', 'paste'] as const).map((value) => (
            <button key={value} type="button" aria-pressed={mode === value} onClick={() => setMode(value)}
              className={`rounded-full px-3 py-1.5 text-[13px] ${mode === value ? 'bg-fill text-ink' : 'text-muted hover:text-ink'}`}>
              {value === 'library' ? 'Research library' : 'Paste notes'}
            </button>
          ))}
        </div>
        {mode === 'library' ? (
          <>
            <div className="mx-6 my-4 flex items-center gap-2 rounded-lg border border-line px-3 focus-within:border-ink">
              <Search size={15} className="shrink-0 text-muted" aria-hidden="true" />
              <input ref={searchInput} autoFocus aria-label="Search research" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search findings, places, or datasets" className="min-w-0 flex-1 bg-transparent py-2 text-sm outline-none placeholder:text-muted" />
            </div>
            <div className="min-h-0 overflow-y-auto px-3 pb-3">
              {error ? <div role="alert" className="px-3 py-8 text-center text-sm text-muted">The library couldn’t load. <button type="button" onClick={() => { setError(false); setAttempt((n) => n + 1) }} className="text-ink underline underline-offset-4">Try again</button>, or paste your notes.</div>
                : !matches ? <p role="status" className="p-8 text-center text-sm text-muted">Loading research…</p>
                : matches.length === 0 ? <p role="status" className="p-8 text-center text-sm text-muted">{query ? 'No matching findings. Try another search.' : 'No research in the library yet. You can paste your own notes.'}</p>
                : <ul aria-label="Research findings">{matches.map((finding) => (
                  <li key={finding.id}>
                    <button type="button" onClick={() => onApply({ title: finding.title, text: finding.reference })} className="group w-full rounded-xl px-3 py-3 text-left transition-colors hover:bg-fill">
                      <span className="mb-1.5 flex items-center gap-2 text-[11px] text-muted"><span>{finding.source.replaceAll('_', ' ')}</span>{finding.verdict && <><span aria-hidden="true">·</span><span>{finding.verdict}</span></>}</span>
                      <span className="flex items-start justify-between gap-3 text-sm font-medium"><span>{finding.title}</span><ArrowUpRight size={16} aria-hidden="true" className="mt-0.5 shrink-0 text-muted group-hover:text-ink" /></span>
                      <span className="mt-1 block text-[13px] leading-relaxed text-muted">{finding.summary}</span>
                    </button>
                  </li>
                ))}</ul>}
            </div>
          </>
        ) : (
          <form className="flex min-h-0 flex-col gap-3 p-6" onSubmit={(event) => {
            event.preventDefault()
            if (text.trim() && !tooLong) onApply({ title: initial?.title ?? 'Research notes', text: text.trim() })
          }}>
            <label htmlFor={`${titleId}-notes`} className="text-[13px]">Notes, findings, or source links</label>
            <textarea ref={notesInput} id={`${titleId}-notes`} autoFocus rows={9} value={text} onChange={(event) => setText(event.target.value)} aria-invalid={tooLong}
              placeholder="Paste prior findings and the evidence behind them…" className="min-h-32 resize-y rounded-xl border border-line bg-transparent p-3 text-sm leading-relaxed outline-none placeholder:text-muted focus:border-ink" />
            {tooLong && <p role="alert" className="text-[13px]">Keep research under 100,000 characters.</p>}
            <div className="flex items-center justify-between gap-3"><span className="text-xs text-muted">Attached to this mission only.</span><button disabled={!text.trim() || tooLong} type="submit" className="rounded-full bg-ink px-4 py-2 text-[13px] text-paper disabled:opacity-40">Attach research</button></div>
          </form>
        )}
      </div>
    </dialog>
  )
}
