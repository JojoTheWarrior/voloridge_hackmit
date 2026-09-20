export function missionPath(missionId: string): string {
  return `/missions/${encodeURIComponent(missionId)}`
}

export function reportPath(missionId: string): string {
  return `${missionPath(missionId)}/report`
}

export function explorerPath(missionId: string): string {
  return `${missionPath(missionId)}/explorer`
}
