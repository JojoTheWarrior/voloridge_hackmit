import type { MissionStatus } from '../types'

const LABELS: Record<MissionStatus, string> = { working: 'Working', waiting: 'Waiting for you', done: 'Done', failed: 'Failed' }

/** Status is carried by shape, not color: filled = working, half-filled = waiting, hollow = done, crossed = failed. */
export function StatusDot({ status }: { status: MissionStatus }) {
  return (
    <svg role="img" aria-label={LABELS[status]} width="8" height="8" viewBox="0 0 8 8" className="shrink-0">
      {status === 'working' ? (
        <circle cx="4" cy="4" r="3" fill="currentColor" className="animate-pulse" />
      ) : (
        <circle cx="4" cy="4" r="2.75" fill="none" stroke="currentColor" strokeWidth="1" />
      )}
      {status === 'waiting' && <path d="M4 1.25a2.75 2.75 0 0 0 0 5.5z" fill="currentColor" />}
      {status === 'failed' && <path d="M1.5 6.5l5-5" stroke="currentColor" strokeWidth="1" strokeLinecap="round" />}
    </svg>
  )
}
