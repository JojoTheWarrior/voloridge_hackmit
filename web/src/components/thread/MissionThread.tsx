import { LoaderCircle } from 'lucide-react'
import { useApi } from '../../api/context'
import { useStickToBottom } from '../../hooks/useStickToBottom'
import type { Mission } from '../../types'
import { EventList } from './EventList'
import { foldWork } from './foldWork'
import { ReplyComposer } from './ReplyComposer'
import { WorkLog } from './WorkLog'

export function MissionThread({ mission, initialDraft = '' }: { mission: Mission; initialDraft?: string }) {
  const api = useApi()
  const { ref, onScroll, stick } = useStickToBottom<HTMLDivElement>(mission.events.length)
  const { opening, work, rest } = foldWork(mission)
  const live = mission.status === 'working'
  const latestStep = mission.events.findLast((event) => event.kind === 'step')
  const latestUpdate = mission.events.findLast((event) => event.kind !== 'user_message')
  const updatedAt = latestUpdate ? new Date(latestUpdate.at) : null

  async function reply(text: string) {
    await api.sendMessage(mission.id, text)
    stick()
  }

  return (
    <div className="flex h-full flex-col">
      <div ref={ref} onScroll={onScroll} role="log" aria-label="Mission thread" className="min-h-0 flex-1 overflow-y-auto">
        <article className="mx-auto flex w-full max-w-[720px] flex-col gap-6 px-6 pt-10 pb-8">
          <EventList events={opening} live={live} />
          <WorkLog events={work} />
          <EventList events={rest} live={live} missionId={mission.id} report={mission.report} explorer={mission.explorer} />
        </article>
      </div>

      <div className="mx-auto w-full max-w-[720px] shrink-0 px-6 pb-5">
        {live && (
          <div role="status" aria-label="Research progress" className="mb-3 flex items-start gap-2.5 rounded-xl bg-fill px-3.5 py-3">
            <LoaderCircle size={15} strokeWidth={1.75} aria-hidden="true" className="mt-0.5 shrink-0 animate-spin" />
            <div className="min-w-0 text-[13px] leading-relaxed">
              <p className="font-medium">Research in progress</p>
              <p className="text-muted">{latestStep?.kind === 'step' ? `Latest step: ${latestStep.label}` : 'Updates and results will appear here as Devin works.'}</p>
              {updatedAt && !Number.isNaN(updatedAt.getTime()) && (
                <p className="mt-1 text-[11px] text-muted">
                  Last update <time dateTime={latestUpdate!.at}>{updatedAt.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</time>
                </p>
              )}
            </div>
          </div>
        )}
        {mission.needsUser && (
          <p className="fade-in mb-2.5 rounded-xl bg-fill px-4 py-2.5 text-[13px] leading-relaxed">
            <span className="text-muted">Devin asks</span> {mission.needsUser}
          </p>
        )}
        <ReplyComposer onSend={reply} initialValue={initialDraft} working={live} />
      </div>
    </div>
  )
}
