import type { Explorer, Mission } from '../types'

export const INSTRUCTIONS_MAX = 2000

const DESCRIPTION = 'Scrub through the window and select any day to see both series and the lag between them.'

export function explorerSrc(missionId: string, version: number): string {
  return `/api/missions/${encodeURIComponent(missionId)}/explorer/${version}/index.html`
}

/** Deterministic mock build. The instructions end up in the description, so a change request visibly changed something. */
export function buildExplorer({ id, title, explorer: previous }: Pick<Mission, 'id' | 'title' | 'explorer'>, instructions: string, builtAt: string): Explorer {
  const version = (previous?.version ?? 0) + 1
  return {
    version,
    title,
    description: instructions ? `${DESCRIPTION} ${instructions}` : DESCRIPTION,
    src: explorerSrc(id, version),
    builtAt,
  }
}
