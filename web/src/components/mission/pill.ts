/** The outline pill every secondary action shares: in the mission header, on the report and around the explorer. */
export const OUTLINE_PILL = 'flex shrink-0 items-center gap-1.5 rounded-full border border-line px-3 py-1 text-[13px] transition-colors duration-150 hover:border-faint'

/** The same pill while its action is unavailable: still in place, visibly at rest, and inert. */
export const RESTING_PILL = `${OUTLINE_PILL} cursor-default text-muted hover:border-line`
