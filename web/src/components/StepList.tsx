import { Check, ChevronRight, LoaderCircle } from 'lucide-react'
import { useState } from 'react'
import { formatElapsed } from '../format'
import { STEP_LABELS } from '../steps'
import type { MissionStatus, MissionStep } from '../types'

interface StepListProps {
  steps: MissionStep[]
  status: MissionStatus
  elapsedSeconds: number
}

function Steps({ steps }: { steps: MissionStep[] }) {
  return (
    <ol aria-label="Progress" className="flex flex-col gap-2 text-[13px]">
      {steps
        .filter((step) => step.state !== 'pending')
        .map((step) =>
          step.state === 'active' ? (
            <li key={step.key} aria-current="step" className="flex items-center gap-2.5">
              <LoaderCircle size={14} strokeWidth={1.75} aria-hidden="true" className="animate-spin" />
              {STEP_LABELS[step.key].active}
            </li>
          ) : (
            <li key={step.key} className="flex items-center gap-2.5 text-muted">
              <Check size={14} strokeWidth={1.75} aria-hidden="true" />
              {step.label}
            </li>
          ),
        )}
    </ol>
  )
}

/** Expanded while the mission runs; folds into one "Worked for" line once it has finished. */
export function StepList({ steps, status, elapsedSeconds }: StepListProps) {
  const [expanded, setExpanded] = useState(false)
  if (status === 'running') return <Steps steps={steps} />

  // A failed mission stopped mid-step; nothing is still in flight.
  const settled = steps.map((step) => (step.state === 'active' ? { ...step, state: 'pending' as const } : step))
  return (
    <div>
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-[13px] text-muted transition-colors duration-150 hover:text-ink"
      >
        Worked for {formatElapsed(elapsedSeconds)}
        <ChevronRight
          size={14}
          strokeWidth={1.75}
          aria-hidden="true"
          className={`transition-transform duration-150 ${expanded ? 'rotate-90' : ''}`}
        />
      </button>
      {expanded && (
        <div className="fade-in mt-3 border-l border-line-soft pl-4">
          <Steps steps={settled} />
        </div>
      )}
    </div>
  )
}
