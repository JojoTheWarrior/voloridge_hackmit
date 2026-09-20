import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { formatReportDate } from '../../format'
import type { Artifact, Mission, Report } from '../../types'
import { ArtifactView } from '../artifacts/ArtifactView'
import { StatGrid } from '../artifacts/StatGrid'
import { CastleLogo } from '../CastleLogo'

function featured({ keyArtifactIds }: Report, events: Mission['events']): Artifact[] {
  const byId = new Map(events.flatMap((e) => (e.kind === 'artifact' ? [[e.artifact.id, e.artifact] as const] : [])))
  return keyArtifactIds.flatMap((id) => byId.get(id) ?? [])
}

function Section({ title, className = '', children }: { title: string; className?: string; children: ReactNode }) {
  return (
    <section aria-label={title} className={className}>
      <h3 className="text-xs text-muted">{title}</h3>
      {children}
    </section>
  )
}

function Bullets({ items }: { items: string[] }) {
  return (
    <ul className="mt-3 flex flex-col gap-2.5 text-sm leading-relaxed">
      {items.map((item, index) => (
        <li key={index}>{item}</li>
      ))}
    </ul>
  )
}

interface ReportDocumentProps {
  mission: Pick<Mission, 'id' | 'title' | 'events'>
  report: Report
  /** Sits beside the eyebrow on screen and stays out of print. */
  actions: ReactNode
}

/** A report typeset like a short paper: the finding first, then what it rests on, then how far to trust it. */
export function ReportDocument({ mission, report, actions }: ReportDocumentProps) {
  const figures = featured(report, mission.events)

  return (
    <article className="fade-in mx-auto w-full max-w-[720px] px-6 pt-5 pb-24 print:max-w-none print:px-0 print:pt-0 print:pb-0">
      <div className="flex min-h-8 flex-wrap items-center justify-between gap-x-4 gap-y-3">
        <p className="text-xs text-muted">
          Mission report <span aria-hidden="true">·</span> <time dateTime={report.generatedAt} className="font-mono">{formatReportDate(report.generatedAt)}</time>
        </p>
        {actions}
      </div>

      <h2 className="mt-10 text-[28px] leading-[1.12] font-medium tracking-[-0.03em] text-balance sm:text-[36px]">{report.headline}</h2>
      <p className="mt-5 text-[17px] leading-[1.65]">{report.summary}</p>

      {report.stats.length > 0 && (
        <div className="mt-10 border-y border-line-soft py-6">
          <StatGrid items={report.stats} />
        </div>
      )}

      {figures.length > 0 && (
        <div className="mt-10 flex flex-col gap-6">
          {figures.map((artifact) => (
            <div key={artifact.id} className="print:break-inside-avoid">
              <ArtifactView artifact={artifact} />
            </div>
          ))}
        </div>
      )}

      {report.steps.length > 0 && (
        <Section title="How we got there" className="mt-14">
          <ol className="mt-4 flex flex-col">
            {report.steps.map((step, index) => (
              <li key={index} className="grid grid-cols-[2rem_minmax(0,1fr)] gap-x-2 border-t border-line-soft py-3.5 first:border-t-0 first:pt-0 print:break-inside-avoid">
                <span className="pt-[3px] font-mono text-xs text-muted">{index + 1}</span>
                <div>
                  <p className="text-[15px] leading-snug font-medium">{step.label}</p>
                  <p className="mt-1 text-sm leading-relaxed text-muted">{step.takeaway}</p>
                </div>
              </li>
            ))}
          </ol>
        </Section>
      )}

      {(report.caveats.length > 0 || report.nextQuestions.length > 0) && (
        <div className="mt-14 grid gap-x-10 gap-y-12 sm:grid-cols-2 print:break-inside-avoid">
          {report.caveats.length > 0 && (
            <Section title="Caveats">
              <Bullets items={report.caveats} />
            </Section>
          )}
          {report.nextQuestions.length > 0 && (
            <Section title="Ask next">
              <ul className="mt-3 flex flex-col gap-2.5 text-sm leading-relaxed">
                {report.nextQuestions.map((question, index) => (
                  <li key={index}><Link to={`/missions/${encodeURIComponent(mission.id)}`} state={{ replyDraft: question }}
                    className="block rounded-sm underline decoration-line underline-offset-4 transition-colors hover:decoration-ink print:no-underline">{question}</Link></li>
                ))}
              </ul>
            </Section>
          )}
        </div>
      )}

      <footer className="mt-16 flex items-center justify-between gap-6 border-t border-line-soft pt-5 text-xs text-muted">
        <span className="flex shrink-0 items-center gap-2 text-ink">
          <CastleLogo size={14} />
          <span aria-hidden="true" className="font-medium tracking-tight">kingdom</span>
        </span>
        <span className="truncate">{mission.title}</span>
      </footer>
    </article>
  )
}
