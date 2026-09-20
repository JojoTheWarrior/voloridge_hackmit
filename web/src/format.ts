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

export function pluralize(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? '' : 's'}`
}

/** How long something took, in the one unit a reader cares about: "14 minutes", "2 hours". Empty when either end is unreadable. */
export function formatElapsed(fromIso: string, toIso: string): string {
  const minutes = Math.floor((Date.parse(toIso) - Date.parse(fromIso)) / 60_000)
  if (Number.isNaN(minutes)) return ''
  if (minutes < 1) return 'under a minute'
  if (minutes < 60) return pluralize(minutes, 'minute')
  if (minutes < 1440) return pluralize(Math.round(minutes / 60), 'hour')
  return pluralize(Math.round(minutes / 1440), 'day')
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** "20 Sep 2026" in the reader's own time zone. Built by hand because locales disagree on "Sep" and "Sept". */
export function formatReportDate(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return `${date.getDate()} ${MONTHS[date.getMonth()]} ${date.getFullYear()}`
}
