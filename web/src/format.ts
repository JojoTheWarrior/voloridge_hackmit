export function formatP(p: number): string {
  return p < 0.001 ? '<0.001' : p.toFixed(3)
}

/** Uses a true minus sign so negative values align and read properly in Geist Mono. */
export function formatCorrelation(r: number): string {
  return r.toFixed(2).replace('-', '−')
}

export function formatLag(days: number): string {
  if (days === 0) return 'Same day'
  return `${days} ${days === 1 ? 'day' : 'days'}`
}

export function formatSynced(iso: string, now: Date = new Date()): string {
  const minutes = Math.floor((now.getTime() - Date.parse(iso)) / 60_000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  if (minutes < 1440) return `${Math.floor(minutes / 60)}h ago`
  return `${Math.floor(minutes / 1440)}d ago`
}
