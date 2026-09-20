const DAY = 86_400_000
const MAX_STEPS = 6
const DAY_STEPS = [1, 2, 7, 14, 30, 91, 182, 365, 730, 1825, 3650]

/** Round tick values (1, 2 or 5 times a power of ten) that fall inside the range. */
export function niceTicks(min: number, max: number): number[] {
  if (!(max > min)) return [min]
  const range = max - min
  const magnitude = 10 ** Math.floor(Math.log10(range / MAX_STEPS))
  const step = ([1, 2, 5].find((factor) => range / (factor * magnitude) <= MAX_STEPS) ?? 10) * magnitude
  const decimals = Math.max(0, -Math.floor(Math.log10(step)))
  const first = Math.ceil(min / step)
  const count = Math.floor(max / step) - first + 1
  // Multiplying an integer index avoids the drift of repeated addition; toFixed trims what is left.
  return Array.from({ length: count }, (_, index) => Number(((first + index) * step).toFixed(decimals)))
}

/** UTC-midnight ticks at the smallest whole-day step that keeps the axis sparse. */
export function dateTicks(min: number, max: number): number[] {
  const days = (max - min) / DAY
  const step = (DAY_STEPS.find((candidate) => days / candidate <= MAX_STEPS) ?? DAY_STEPS[DAY_STEPS.length - 1]) * DAY
  const first = Math.ceil(min / step)
  const count = Math.floor(max / step) - first + 1
  return count > 0 ? Array.from({ length: count }, (_, index) => (first + index) * step) : [min]
}
