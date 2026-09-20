import type { Mission, Report } from '../types'

const MAX_FIGURES = 3
const MAX_STATS = 4
const MAX_STEPS = 8

const TAKEAWAYS: Record<string, string> = {
  s1: 'Both sources cover the same window, with no gaps worth worrying about.',
  s2: 'Daily values, standardized so the two series can share an axis.',
  s3: 'One lag stood out from the rest and beat shuffled data.',
  s4: 'The link keeps its sign in each half of the window and without the largest moves.',
}
const TAKEAWAY_FALLBACK = 'Finished without surprises.'

// A rewrite keeps the finding and changes the framing, which is what asking Devin again tends to do.
const CLOSERS = [
  'The figures below show what that rests on, and the caveats say how far to trust it.',
  'What follows is the evidence for that, step by step, and what it leaves open.',
  'The rest of this report lays out the evidence and its limits.',
]

const CAVEATS = [
  'A correlation over one window is not a causal claim.',
  'A shared driver, such as the season, could move both series.',
  'Daily values are autocorrelated, so the effective sample is smaller than the day count suggests.',
]

const NEXT_QUESTIONS = [
  'Does the result hold over a two-year window?',
  'Does it survive controlling for the season?',
  'Is the effect stronger on weekdays than on weekends?',
]

/** The opening clause of a write-up; a full stop inside a number or a name like PM2.5 does not end it. */
function firstClause(text: string): string {
  return text.split(/[.,](?:\s|$)/)[0]
}

/** Deterministic mock report, read off the thread the way Devin looks back over its session. */
export function buildReport({ title, events, report: previous }: Pick<Mission, 'title' | 'events' | 'report'>, generatedAt: string): Report {
  const conclusion = events.findLast((e) => e.kind === 'conclusion')
  const steps = events.filter((e) => e.kind === 'step')
  const opening = conclusion
    ? conclusion.summary.split('\n')[0]
    : `Devin has not reached a conclusion on this question yet. So far it has worked through ${steps.length} ${steps.length === 1 ? 'step' : 'steps'}.`
  const summaries = CLOSERS.map((closer) => `${opening} ${closer}`)

  return {
    headline: conclusion ? firstClause(conclusion.summary) : `${title}: no conclusion yet`,
    summary: summaries.find((summary) => summary !== previous?.summary)!,
    stats: conclusion?.stats.slice(0, MAX_STATS) ?? [],
    keyArtifactIds: events.flatMap((e) => (e.kind === 'artifact' ? [e.artifact.id] : [])).slice(0, MAX_FIGURES),
    steps: steps.slice(0, MAX_STEPS).map((step) => ({ label: step.label, takeaway: TAKEAWAYS[step.stepId] ?? TAKEAWAY_FALLBACK })),
    caveats: [...CAVEATS],
    nextQuestions: [...NEXT_QUESTIONS],
    generatedAt,
  }
}
