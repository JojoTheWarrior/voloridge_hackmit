import { useState, type FormEvent } from 'react'
import { ValidationError } from '../../api/index'
import { CenteredState } from '../mission/CenteredState'
import { OUTLINE_PILL, RESTING_PILL } from '../mission/pill'

const QUIET_LINE = 'max-w-md text-sm leading-relaxed text-muted'

interface ExplorerInvitationProps {
  /** Without a conclusion Devin has less to build on; it is still the user's call. */
  concluded: boolean
  /** The request is on its way; the form stays so that nothing typed is lost if it fails. */
  busy: boolean
  onBuild: (instructions: string) => Promise<void>
}

export function ExplorerInvitation({ concluded, busy, onBuild }: ExplorerInvitationProps) {
  const [wish, setWish] = useState('')
  const [problem, setProblem] = useState<string>()

  async function submit(event: FormEvent) {
    event.preventDefault()
    setProblem(undefined)
    try {
      await onBuild(wish.trim())
    } catch (caught) {
      setProblem(caught instanceof ValidationError ? caught.message : 'That did not send. Try again.')
    }
  }

  return (
    <CenteredState title="Explore the findings">
      <p className={QUIET_LINE}>When the findings are places or items rather than statistics, Devin can build an interactive page for them: a map to pan, a list to rank, the evidence behind each one.</p>
      <p className={QUIET_LINE}>Not every mission needs one.{concluded ? '' : ' Devin has not reached a conclusion yet, and it is usually worth waiting for one.'}</p>
      <form onSubmit={submit} noValidate className="mt-4 flex w-full max-w-md flex-col items-center gap-3">
        <input
          aria-label="Anything specific it should show?"
          value={wish}
          onChange={(event) => setWish(event.target.value)}
          placeholder="Anything specific it should show?"
          autoComplete="off"
          className="block w-full rounded-lg border border-line bg-transparent px-3 py-2 text-center text-sm outline-none transition-colors duration-150 placeholder:text-faint focus:border-ink"
        />
        <button type="submit" aria-disabled={busy} className={`${busy ? RESTING_PILL : OUTLINE_PILL} px-4 py-1.5`}>
          Build explorer
        </button>
        {problem && (
          <p role="status" className="text-[13px] text-muted">
            {problem}
          </p>
        )}
      </form>
    </CenteredState>
  )
}
