import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../api/context'
import { EXAMPLE_PROMPTS } from '../examples'
import { Composer } from '../components/Composer'
import { useDatasets } from '../hooks/useApiData'

export function NewMissionPage() {
  const api = useApi()
  const navigate = useNavigate()
  const datasets = useDatasets() ?? []
  const [prompt, setPrompt] = useState('')
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const submitting = useRef(false)

  async function start(hypothesis: string, datasetIds: string[]) {
    if (submitting.current) return
    submitting.current = true
    try {
      const mission = await api.createMission({ hypothesis, datasetIds })
      // Stay locked on success: the page is about to unmount, and a second Enter must not start a twin.
      navigate(`/missions/${mission.id}`)
    } catch (error) {
      submitting.current = false
      throw error
    }
  }

  return (
    <div className="flex min-h-full flex-col items-center justify-center px-6 pt-10 pb-28">
      <div className="w-full max-w-[640px]">
        <h1 className="mb-7 text-center text-[32px] leading-tight font-medium tracking-[-0.03em]">
          What should we look into?
        </h1>
        <Composer datasets={datasets} value={prompt} onChange={setPrompt} onSubmit={start} inputRef={inputRef} />

        <div className="mt-9">
          <div className="px-1 pb-2 text-xs text-muted">Try one</div>
          <div className="flex flex-col gap-1.5">
            {EXAMPLE_PROMPTS.map((example) => (
              <button
                key={example}
                type="button"
                onClick={() => {
                  setPrompt(example)
                  inputRef.current?.focus()
                }}
                className="rounded-lg border border-line-soft px-3.5 py-2.5 text-left text-[13px] text-muted transition-colors duration-150 hover:border-line hover:text-ink"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
