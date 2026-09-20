import type { Report } from '../types'

/** The seeded report's own words; its stats and timestamp come from the thread it is attached to. */
export type ReportText = Omit<Report, 'stats' | 'generatedAt'>

/** Written for the `houston-heat-gas` seed. The numbers it quotes are the ones that mission's findings compute. */
export const HOUSTON_REPORT: ReportText = {
  headline: 'Houston heat shows up in Henry Hub gas prices two days later',
  summary:
    'When Houston runs hotter than normal, the Henry Hub spot price tends to rise two days afterwards. Over 120 days the two series correlate at 0.62 once temperature is shifted two days ahead. The link beats shuffled data, holds in both halves of the window, and does not rest on a handful of extreme days. That makes it a signal worth watching, though not yet proof that heat is the cause.',
  keyArtifactIds: ['a1', 'a2', 'a3'],
  steps: [
    { label: 'Read the linked datasets', takeaway: 'Open-Meteo temperatures and Yahoo Finance spot prices cover the same 120 days, with no gaps.' },
    { label: 'Align the two series', takeaway: 'Daily values, standardized so heat and price can share an axis.' },
    { label: 'Test the relationship at each lag', takeaway: 'Correlation peaks at 0.62 when heat leads by two days and fades on either side.' },
    { label: 'Check that it holds on parts of the window', takeaway: 'It reads 0.48 in the first half, 0.75 in the second, and 0.57 without the five largest price moves.' },
  ],
  caveats: [
    'A correlation over one summer is not a causal claim.',
    'Hurricane season sits inside the window and could drive both heat and prices.',
    'The link is stronger in the second half, so it may be recent rather than stable.',
    'Daily values are autocorrelated, so the effective sample is closer to 30 days than 120.',
  ],
  nextQuestions: [
    'Does the two-day lead hold over the last three summers?',
    'Does it survive controlling for storage reports and hurricane alerts?',
    'Is the effect stronger in heat waves than on ordinary warm days?',
  ],
}
