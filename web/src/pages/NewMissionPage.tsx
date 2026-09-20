import { useRef, useState } from 'react'
import { ArrowUpRight, Paperclip, RefreshCw, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../api/context'
import { STARTER_DATASETS, STARTER_IDEAS } from '../examples'
import { Composer } from '../components/Composer'
import { ResearchDialog, type ResearchAttachment } from '../components/ResearchDialog'
import { ValidationError } from '../api/index'
import { useDatasets } from '../hooks/useApiData'

export function NewMissionPage() {
  const api = useApi()
  const navigate = useNavigate()
  const datasets = useDatasets() ?? []
  const [prompt, setPrompt] = useState('')
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const submitting = useRef(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [research, setResearch] = useState<ResearchAttachment>()
  const [researchOpen, setResearchOpen] = useState(false)
  const [ideaPage, setIdeaPage] = useState(0)
  const [suggestion, setSuggestion] = useState<{ key: number; datasetIds: string[] }>()
  const ideas = STARTER_IDEAS.slice(ideaPage * 3, ideaPage * 3 + 3)

  async function start(hypothesis: string, datasetIds: string[]) {
    if (submitting.current) return
    submitting.current = true
    setBusy(true)
    setError('')
    try {
      const mission = await api.createMission({ hypothesis, datasetIds, ...(research ? { reference: research.text } : {}) })
      // Stay locked on success: the page is about to unmount, and a second Enter must not start a twin.
      navigate(`/missions/${mission.id}`)
    } catch (error) {
      submitting.current = false
      setBusy(false)
      setError(error instanceof ValidationError ? error.message : 'Couldn’t start the mission. Check your connection and try again.')
    }
  }

  return (
    <div className="flex min-h-full flex-col items-center justify-center px-6 pt-10 pb-28">
      <div className="w-full max-w-[640px]">
        <h1 className="mb-7 text-center text-[32px] leading-tight font-medium tracking-[-0.03em]">
          What should we look into?
        </h1>
        <Composer key={suggestion?.key ?? 0} datasets={datasets} value={prompt} onChange={setPrompt} onSubmit={start} inputRef={inputRef} busy={busy} initialDatasetIds={suggestion?.datasetIds} />
        {error && <p role="alert" className="mt-3 px-1 text-[13px]">{error}</p>}
        <div className="mt-3 flex min-w-0 items-center gap-1 text-[13px] text-muted">
          <button type="button" disabled={busy} onClick={() => setResearchOpen(true)} className="flex min-w-0 items-center gap-2 rounded-lg px-2 py-1.5 text-left hover:bg-fill hover:text-ink">
            <Paperclip size={14} className="shrink-0" aria-hidden="true" /><span className="truncate">{research?.title ?? 'Attach research'}</span>
          </button>
          {research && <button type="button" disabled={busy} aria-label="Remove research" onClick={() => setResearch(undefined)} className="shrink-0 rounded-full p-1.5 hover:bg-fill hover:text-ink"><X size={14} /></button>}
        </div>
        {researchOpen && <ResearchDialog initial={research} onClose={() => setResearchOpen(false)} onApply={(attachment) => {
          setResearch(attachment)
          if (!prompt.trim()) setPrompt(`Investigate: ${attachment.title}`)
          setResearchOpen(false)
          inputRef.current?.focus()
        }} />}

        <div className="mt-9">
          <div className="flex items-center justify-between px-1 pb-2 text-xs text-muted">
            <span>Connections to explore</span>
            <button type="button" disabled={busy} onClick={() => setIdeaPage((page) => (page + 1) % Math.ceil(STARTER_IDEAS.length / 3))}
              className="flex items-center gap-1.5 rounded-md px-1.5 py-1 transition-colors hover:bg-fill hover:text-ink disabled:opacity-50">
              <RefreshCw size={12} aria-hidden="true" /> More ideas
            </button>
          </div>
          <div className="flex flex-col gap-1.5">
            {ideas.map((idea) => (
              <button
                key={idea.text}
                type="button"
                aria-label={idea.text}
                disabled={busy || datasets.length === 0}
                onClick={() => {
                  setPrompt(idea.text)
                  setSuggestion((previous) => ({ key: (previous?.key ?? 0) + 1, datasetIds: idea.datasetIds }))
                  inputRef.current?.focus()
                }}
                className="group rounded-xl border border-line-soft px-3.5 py-3 text-left transition-colors duration-150 hover:border-line hover:bg-fill disabled:pointer-events-none disabled:opacity-50"
              >
                <span className="flex items-start justify-between gap-3 text-[13px] leading-relaxed text-ink"><span>{idea.text}</span><ArrowUpRight size={14} aria-hidden="true" className="mt-0.5 shrink-0 text-muted" /></span>
                <span className="mt-2 block text-[11px] text-muted">{idea.datasetIds.map((id) => STARTER_DATASETS.find((dataset) => dataset.id === id)?.name).filter(Boolean).join(' · ')}</span>
              </button>
            ))}
          </div>
          <p className="mt-2 px-1 text-[11px] text-muted">Suggested by Devin. Choose one to make it your own.</p>
        </div>
      </div>
    </div>
  )
}
