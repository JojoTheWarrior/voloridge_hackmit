import type { ReactNode } from 'react'
import { hash, mulberry32 } from '../random'
import type { DatasetKind } from '../types'

const INK = '#0a0a0a'
const FAINT = '#bdbdbd'
const LINE = '#e5e5e5'
const WIDTH = 320
const HEIGHT = 120
const STROKE = { fill: 'none', strokeWidth: 1.5, strokeLinecap: 'round', strokeLinejoin: 'round' } as const

type Rand = () => number
type Point = [x: number, y: number]

const round = (value: number) => Math.round(value * 10) / 10
const range = (count: number) => Array.from({ length: count }, (_, i) => i)
const toPath = (points: Point[]) => points.map(([x, y], i) => `${i ? 'L' : 'M'}${round(x)} ${round(y)}`).join('')

/** A few soft bumps; sampling their sum gives a field that clusters instead of looking like static. */
function bumps(rand: Rand, count: number, spread: number) {
  const centers = range(count).map(() => ({ x: 0.15 + rand() * 0.7, y: 0.25 + rand() * 0.5, reach: spread * (0.7 + rand() * 0.6), weight: 0.6 + rand() * 0.4 }))
  return (x: number, y = 0.5) =>
    centers.reduce((sum, c) => sum + c.weight * Math.exp(-(((x - c.x) / c.reach) ** 2) - ((y - c.y) / (c.reach * 2.4)) ** 2), 0)
}

/** Dot histogram on a timeline: a quiet row of daily dots, with a few bursts stacked in ink. */
function events(rand: Rand): ReactNode {
  const STEP = 8
  const BASE = 92
  const density = bumps(rand, 4, 0.08)
  const columns = range(WIDTH / STEP - 1).map((i) => {
    const x = (i + 1) * STEP
    return { x, count: Math.min(9, 1 + Math.floor(density(x / WIDTH) * 6.5 + rand() * 1.8)) }
  })
  return columns.flatMap(({ x, count }) =>
    range(count).map((k) => <circle key={`${x}-${k}`} cx={x} cy={BASE - k * STEP} r={1.5} fill={count >= 5 ? INK : FAINT} />),
  )
}

function walk(rand: Rand, steps: number, follow?: number[]): number[] {
  let value = 0
  return range(steps).map((i) => {
    value += (rand() - 0.5) * 2 + (follow ? (follow[i] - value) * 0.18 : 0.06)
    return value
  })
}

/** Price line in ink over a fainter, related series. */
function markets(rand: Rand): ReactNode {
  const STEPS = 65
  const price = walk(rand, STEPS)
  const peer = walk(rand, STEPS, price).map((v) => v * 0.7)
  const all = [...price, ...peer]
  const low = Math.min(...all)
  const span = Math.max(...all) - low || 1
  const plot = (values: number[], lift: number): Point[] =>
    values.map((v, i) => [(i / (STEPS - 1)) * WIDTH, 94 - ((v - low) / span) * 64 + lift])
  return (
    <>
      {[30, 60, 90].map((y) => (
        <path key={y} d={`M0 ${y}H${WIDTH}`} stroke={LINE} strokeWidth={1} />
      ))}
      <path d={toPath(plot(peer, 8))} stroke={FAINT} {...STROKE} />
      <path d={toPath(plot(price, 0))} stroke={INK} {...STROKE} />
    </>
  )
}

/** Overlapping seasonal waves, the front one in ink. */
function weather(rand: Rand): ReactNode {
  const waves = [LINE, FAINT, INK].map((stroke, layer) => ({
    stroke,
    middle: 46 + layer * 14,
    swing: 14 + rand() * 8,
    period: 150 + rand() * 90,
    phase: rand() * Math.PI * 2,
    ripple: 2 + rand() * 3,
  }))
  return waves.map(({ stroke, middle, swing, period, phase, ripple }) => {
    const points = range(WIDTH / 4 + 1).map((i): Point => {
      const angle = ((i * 4) / period) * Math.PI * 2 + phase
      return [i * 4, middle + swing * Math.sin(angle) + ripple * Math.sin(angle * 3.1 + phase)]
    })
    return <path key={stroke} d={toPath(points)} stroke={stroke} {...STROKE} />
  })
}

/** Halftone plume: dots grow and darken where the concentration is highest. */
function air(rand: Rand): ReactNode {
  const STEP = 10
  const density = bumps(rand, 3, 0.16)
  return range(HEIGHT / STEP - 1).flatMap((row) =>
    range(WIDTH / STEP).map((column) => {
      const x = column * STEP + (row % 2 ? STEP : STEP / 2)
      const y = (row + 1) * STEP
      const level = Math.min(1, density(x / WIDTH, y / HEIGHT) + rand() * 0.08)
      return <circle key={`${row}-${column}`} cx={x} cy={y} r={round(0.8 + level * 1.8)} fill={level > 0.8 ? INK : level > 0.3 ? FAINT : LINE} />
    }),
  )
}

/** Nothing known about the data yet: an even grid with a handful of dots picked out. */
function other(rand: Rand): ReactNode {
  const STEP = 16
  const ROWS = 6
  const top = (HEIGHT - (ROWS - 1) * STEP) / 2
  return range(ROWS).flatMap((row) =>
    range(WIDTH / STEP - 1).map((column) => (
      <circle key={`${row}-${column}`} cx={(column + 1) * STEP} cy={top + row * STEP} r={1.5} fill={rand() < 0.08 ? INK : FAINT} />
    )),
  )
}

const DRAW: Record<DatasetKind, (rand: Rand) => ReactNode> = { events, markets, weather, air, other }

/** Decorative hint at what a dataset holds. Seeded from the id, so it never changes between renders. */
export function DatasetThumbnail({ id, kind }: { id: string; kind: DatasetKind }) {
  return (
    <div className="h-[120px] border-b border-line bg-side">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false" className="block h-full w-full">
        {DRAW[kind](mulberry32(hash(id)))}
      </svg>
    </div>
  )
}
