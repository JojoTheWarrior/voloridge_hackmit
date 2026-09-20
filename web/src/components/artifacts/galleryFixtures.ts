import type { Artifact } from '../../types'

/** Small deterministic generator so the gallery looks the same on every load. */
function sequence(seed: number) {
  let state = seed
  return () => {
    state = (state * 1664525 + 1013904223) % 4294967296
    return state / 4294967296
  }
}

const day = (offset: number) => new Date(Date.UTC(2026, 5, 1 + offset)).toISOString().slice(0, 10)

function scatterPoints(count: number): [number, number][] {
  const next = sequence(7)
  return Array.from({ length: count }, () => {
    const share = next() * 0.6
    const hours = 2.5 + share * 14 + (next() - 0.5) * 7
    return [Number(share.toFixed(3)), Number(Math.max(0.4, hours).toFixed(2))]
  })
}

function dailySeries(seed: number, base: number, drift: number): [string, number][] {
  const next = sequence(seed)
  let level = base
  return Array.from({ length: 60 }, (_, index) => {
    level += (next() - 0.5) * drift + (index > 30 ? drift * 0.12 : 0)
    return [day(index), Number(level.toFixed(2))]
  })
}

export const galleryArtifacts: Artifact[] = [
  {
    id: 'g-scatter',
    type: 'chart',
    kind: 'scatter',
    title: 'Severe damage share vs outage length',
    headline: 'r = 0.58',
    xLabel: 'Share of tiles classed severe',
    yLabel: 'Median outage hours',
    series: [{ name: 'Counties', points: scatterPoints(120) }],
    caption: 'Each dot is one county-storm pair. The relationship holds after dropping the three largest metros.',
  },
  {
    id: 'g-line',
    type: 'chart',
    kind: 'line',
    title: 'Conflict events and Brent, standardized',
    headline: 'lag 3d',
    yLabel: 'z-score',
    series: [
      { name: 'GDELT Iran events', points: dailySeries(3, 0, 0.9) },
      { name: 'Brent crude', points: dailySeries(11, 0.2, 0.7) },
    ],
    caption: 'Daily values, 1 June to 30 July 2026.',
  },
  {
    id: 'g-bar',
    type: 'chart',
    kind: 'bar',
    title: 'Median outage hours by damage class',
    xLabel: 'Damage class',
    yLabel: 'Hours',
    series: [{ name: 'Median hours', points: [['None', 2.1], ['Minor', 3.4], ['Moderate', 6.8], ['Severe', 11.9], ['Destroyed', 17.3]] }],
  },
  {
    id: 'g-images',
    type: 'images',
    title: 'Sample tiles from the imagery set',
    items: [
      { src: 'https://picsum.photos/seed/11/640/480', caption: 'Harris County, severe' },
      { src: 'https://picsum.photos/seed/12/640/480', caption: 'Galveston, moderate' },
      { src: 'https://picsum.photos/seed/13/640/480', caption: 'Brazoria, minor' },
      { src: 'https://picsum.photos/seed/14/640/480', caption: 'Fort Bend, none' },
    ],
    caption: '2,140 tiles in total, each 512 px square at 0.5 m resolution.',
  },
  {
    id: 'g-relation-small',
    type: 'relation',
    title: 'How the two datasets join',
    nodes: [
      { id: 'tiles', label: 'Imagery tiles' },
      { id: 'county', label: 'County-day' },
      { id: 'outages', label: 'Outage reports' },
    ],
    edges: [
      { from: 'tiles', to: 'county', label: 'centroid' },
      { from: 'outages', to: 'county', label: 'FIPS + date' },
    ],
  },
  {
    id: 'g-relation-large',
    type: 'relation',
    title: 'Analysis pipeline',
    nodes: [
      { id: 'gdelt', label: 'GDELT events' },
      { id: 'brent', label: 'Brent futures' },
      { id: 'weather', label: 'Open-Meteo' },
      { id: 'filter', label: 'Iran filter' },
      { id: 'daily', label: 'Daily counts' },
      { id: 'returns', label: 'Log returns' },
      { id: 'season', label: 'Deseasonalize' },
      { id: 'align', label: 'Align calendars' },
      { id: 'lag', label: 'Lag search' },
      { id: 'placebo', label: 'Placebo shuffle' },
      { id: 'granger', label: 'Granger test' },
      { id: 'verdict', label: 'Verdict' },
    ],
    edges: [
      { from: 'gdelt', to: 'filter' },
      { from: 'filter', to: 'daily', label: 'count' },
      { from: 'brent', to: 'returns' },
      { from: 'weather', to: 'season' },
      { from: 'daily', to: 'align' },
      { from: 'returns', to: 'align' },
      { from: 'season', to: 'align', label: 'control' },
      { from: 'align', to: 'lag' },
      { from: 'lag', to: 'granger', label: 'best lag' },
      { from: 'lag', to: 'placebo' },
      { from: 'granger', to: 'verdict' },
      { from: 'placebo', to: 'verdict' },
      { from: 'returns', to: 'verdict', label: 'baseline' },
    ],
    caption: 'Every branch was run; the placebo shuffle used 1,000 permutations.',
  },
  {
    id: 'g-table',
    type: 'table',
    title: 'Robustness checks',
    columns: ['Specification', 'r', 'p-value', 'n'],
    rows: [
      ['Baseline', '0.58', '<0.001', '412'],
      ['Without top 3 metros', '0.54', '<0.001', '409'],
      ['Coastal counties only', '0.61', '0.002', '96'],
      ['Shuffled storm dates', '-0.03', '0.71', '412'],
    ],
  },
  {
    id: 'g-stats',
    type: 'stats',
    title: 'Core statistics',
    items: [
      { label: 'Correlation', value: '0.58' },
      { label: 'Best lag', value: '3 days' },
      { label: 'p-value', value: '<0.001' },
      { label: 'Sample', value: '412' },
    ],
    caption: 'Falsified if the correlation drops below 0.3 on the 2027 storm season.',
  },
  {
    id: 'g-image',
    type: 'image',
    title: 'Residual map',
    src: 'https://picsum.photos/seed/21/1280/640',
    caption: 'Residuals cluster along the coast, which points to grid age rather than storm strength.',
  },
]
