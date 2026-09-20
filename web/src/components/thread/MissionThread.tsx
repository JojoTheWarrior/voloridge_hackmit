import { useApi } from '../../api/context'
import { useStickToBottom } from '../../hooks/useStickToBottom'
import type { Mission } from '../../types'
import { EventList } from './EventList'
import { foldWork } from './foldWork'
import { ReplyComposer } from './ReplyComposer'
import { WorkLog } from './WorkLog'

export function MissionThread({ mission }: { mission: Mission }) {
  const api = useApi()
  const { ref, onScroll, stick } = useStickToBottom<HTMLDivElement>(mission.events.length)
  const { opening, work, rest } = foldWork(mission)
  const live = mission.status === 'working'

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
        {mission.needsUser && (
          <p className="fade-in mb-2.5 rounded-xl bg-fill px-4 py-2.5 text-[13px] leading-relaxed">
            <span className="text-muted">Devin asks</span> {mission.needsUser}
          </p>
        )}
        <ReplyComposer onSend={reply} />
      </div>
    </div>
  )
}
