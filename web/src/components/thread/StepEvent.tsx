import { Check, LoaderCircle, Minus } from 'lucide-react'
import type { StepState } from '../../types'

interface StepEventProps {
  label: string
  state: StepState
  /** Whether Devin is working right now. A step left active by a mission that stopped is not in flight. */
  live: boolean
}

export function StepEvent({ label, state, live }: StepEventProps) {
  const running = state === 'active' && live
  const Icon = running ? LoaderCircle : state === 'done' ? Check : Minus
  return (
    <p data-step aria-current={running ? 'step' : undefined} className={`flex items-center gap-2.5 text-[13px] ${running ? '' : 'text-muted'}`}>
      <Icon size={14} strokeWidth={1.75} aria-hidden="true" className={`shrink-0 ${running ? 'animate-spin' : ''}`} />
      {label}
    </p>
  )
}
