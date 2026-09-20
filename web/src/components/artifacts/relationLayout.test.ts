import { layoutRelation, type PlacedNode } from './relationLayout'

const nodes = (...ids: string[]) => ids.map((id) => ({ id, label: id.toUpperCase() }))
const edge = (from: string, to: string, label?: string) => ({ from, to, label })
const byId = (placed: PlacedNode[]) => Object.fromEntries(placed.map((node) => [node.id, node]))
const centerY = (node: PlacedNode) => node.y + node.height / 2
const overlaps = (a: PlacedNode, b: PlacedNode) =>
  a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height

/** First and last coordinates of an SVG path made of M, C and L commands. */
function endpoints(path: string) {
  const numbers = path.match(/-?\d+(\.\d+)?/g)!.map(Number)
  return { start: numbers.slice(0, 2), end: numbers.slice(-2) }
}

describe('layoutRelation', () => {
  it('returns an empty layout for no nodes', () => {
    expect(layoutRelation([], [])).toEqual({ width: 0, height: 0, nodes: [], edges: [] })
  })

  it('tolerates missing arrays and junk entries', () => {
    const layout = layoutRelation([null, { id: 'a' }, { label: 'no id' }, { id: 7, label: 'Seven' }], undefined)
    expect(layout.nodes.map((node) => [node.id, node.label])).toEqual([
      ['a', 'a'],
      ['7', 'Seven'],
    ])
    expect(layoutRelation(undefined, [edge('a', 'b')]).nodes).toEqual([])
  })

  it('places two linked nodes left to right on one line, joined edge to edge', () => {
    const layout = layoutRelation(nodes('a', 'b'), [edge('a', 'b', 'joins')])
    const { a, b } = byId(layout.nodes)
    expect([a.layer, b.layer]).toEqual([0, 1])
    expect(a.x + a.width).toBeLessThan(b.x)
    expect(centerY(a)).toBe(centerY(b))

    const [link] = layout.edges
    const { start, end } = endpoints(link.path)
    expect(start[0]).toBeGreaterThanOrEqual(a.x + a.width)
    expect(end[0]).toBeLessThanOrEqual(b.x)
    expect(start[1]).toBe(centerY(a))
    expect(link.label).toBe('joins')
    expect(link.labelX).toBeGreaterThan(a.x + a.width)
    expect(link.labelX).toBeLessThan(b.x)
  })

  it('layers by the longest path from a source', () => {
    const layout = layoutRelation(nodes('a', 'b', 'c'), [edge('a', 'c'), edge('a', 'b'), edge('b', 'c')])
    const { a, b, c } = byId(layout.nodes)
    expect([a.layer, b.layer, c.layer]).toEqual([0, 1, 2])
  })

  it('routes an edge that skips a layer around the nodes in between', () => {
    const layout = layoutRelation(nodes('a', 'b', 'c'), [edge('a', 'b'), edge('b', 'c'), edge('a', 'c')])
    const { b } = byId(layout.nodes)
    const long = layout.edges.find((link) => link.from === 'a' && link.to === 'c')!
    const run = long.path.match(/L (-?[\d.]+) (-?[\d.]+)/)!
    const runY = Number(run[2])
    expect(runY < b.y || runY > b.y + b.height).toBe(true)
  })

  it('keeps a chain straight and lets the long edge beside it take the detour', () => {
    const layout = layoutRelation(nodes('a', 'b', 'c', 'd'), [edge('a', 'b'), edge('b', 'c'), edge('c', 'd'), edge('a', 'd')])
    const { a, b, c, d } = byId(layout.nodes)
    expect([centerY(b), centerY(c), centerY(d)]).toEqual([centerY(a), centerY(a), centerY(a)])
  })

  it('only moves the nodes that actually collide', () => {
    const layout = layoutRelation(nodes('a', 'b', 'c', 'd', 'e'), [edge('a', 'c'), edge('b', 'd'), edge('b', 'e')])
    const { a, c } = byId(layout.nodes)
    expect(centerY(c)).toBe(centerY(a))
  })

  it('puts labels where edges are spread apart: by the sources of a fan-in, by the targets of a fan-out', () => {
    const fanIn = layoutRelation(nodes('a', 'b', 'c'), [edge('a', 'c', 'one'), edge('b', 'c', 'two')])
    const inNodes = byId(fanIn.nodes)
    const inMiddle = (inNodes.a.x + inNodes.a.width + inNodes.c.x) / 2
    for (const link of fanIn.edges) expect(link.labelX).toBeLessThan(inMiddle)
    expect(Math.abs(fanIn.edges[0].labelY - fanIn.edges[1].labelY)).toBeGreaterThan(20)

    const fanOut = layoutRelation(nodes('a', 'b', 'c'), [edge('a', 'b', 'one'), edge('a', 'c', 'two')])
    const outNodes = byId(fanOut.nodes)
    const outMiddle = (outNodes.a.x + outNodes.a.width + outNodes.b.x) / 2
    for (const link of fanOut.edges) expect(link.labelX).toBeGreaterThan(outMiddle)
  })

  it('leaves room for an off-centre label between its node and the curve', () => {
    const layout = layoutRelation(nodes('a', 'b', 'c'), [edge('a', 'c', 'a fairly long label'), edge('b', 'c', 'x')])
    const { a } = byId(layout.nodes)
    const label = layout.edges[0]
    const halfWidth = (label.label!.length * 6.6) / 2
    expect(label.labelX - halfWidth).toBeGreaterThan(a.x + a.width)
  })

  it('breaks cycles deterministically and still draws every edge', () => {
    const layout = layoutRelation(nodes('a', 'b', 'c'), [edge('a', 'b'), edge('b', 'c'), edge('c', 'a')])
    const { a, b, c } = byId(layout.nodes)
    expect([a.layer, b.layer, c.layer]).toEqual([0, 1, 2])
    expect(layout.edges).toHaveLength(3)

    const back = layout.edges.find((link) => link.from === 'c')!
    const { start, end } = endpoints(back.path)
    expect(start[0]).toBeLessThanOrEqual(c.x)
    expect(end[0]).toBeGreaterThanOrEqual(a.x + a.width)
  })

  it('attaches a back-edge below centre so its arrowhead does not sit on the forward edge', () => {
    const layout = layoutRelation(nodes('a', 'b'), [edge('a', 'b'), edge('b', 'a')])
    const [forward, back] = layout.edges.map((link) => endpoints(link.path))
    expect(back.end[1]).toBeGreaterThan(forward.start[1])
    expect(back.start[1]).toBeGreaterThan(forward.end[1])
  })

  it('handles a two-node cycle', () => {
    const layout = layoutRelation(nodes('a', 'b'), [edge('a', 'b'), edge('b', 'a')])
    expect(layout.nodes.map((node) => node.layer)).toEqual([0, 1])
    expect(layout.edges).toHaveLength(2)
  })

  it('ignores self-loops, duplicate edges and edges to unknown nodes', () => {
    const layout = layoutRelation(nodes('a', 'b'), [
      edge('a', 'a'),
      edge('a', 'b'),
      edge('a', 'b', 'again'),
      edge('a', 'ghost'),
      edge('ghost', 'b'),
      null,
    ])
    expect(layout.edges.map((link) => [link.from, link.to, link.label])).toEqual([['a', 'b', undefined]])
  })

  it('keeps the first of duplicate node ids', () => {
    const layout = layoutRelation(
      [
        { id: 'a', label: 'First' },
        { id: 'a', label: 'Second' },
      ],
      [],
    )
    expect(layout.nodes.map((node) => node.label)).toEqual(['First'])
  })

  it('stacks disconnected nodes in the first layer without overlap', () => {
    const layout = layoutRelation(nodes('a', 'b', 'c'), [])
    expect(layout.nodes.map((node) => node.layer)).toEqual([0, 0, 0])
    const ys = layout.nodes.map((node) => node.y)
    expect(ys[1]).toBeGreaterThanOrEqual(ys[0] + layout.nodes[0].height)
    expect(ys[2]).toBeGreaterThanOrEqual(ys[1] + layout.nodes[1].height)
  })

  it('orders a layer by where its parents sit, to avoid crossings', () => {
    const layout = layoutRelation(nodes('a', 'b', 'c', 'd'), [edge('a', 'd'), edge('b', 'c')])
    const { a, b, c, d } = byId(layout.nodes)
    expect(a.y).toBeLessThan(b.y)
    expect(d.y).toBeLessThan(c.y)
  })

  it('centres a parent against its children', () => {
    const layout = layoutRelation(nodes('a', 'b', 'c', 'd'), [edge('a', 'b'), edge('a', 'c'), edge('a', 'd')])
    const { a, c } = byId(layout.nodes)
    expect(centerY(a)).toBe(centerY(c))
  })

  it('truncates absurd labels but keeps the full text', () => {
    const long = 'x'.repeat(200)
    const layout = layoutRelation(
      [
        { id: 'a', label: long },
        { id: 'b', label: 'B' },
      ],
      [{ from: 'a', to: 'b', label: long }],
    )
    const [a] = layout.nodes
    expect(a.label.length).toBeLessThanOrEqual(27)
    expect(a.label.endsWith('…')).toBe(true)
    expect(a.fullLabel).toBe(long)
    expect(layout.edges[0].label!.length).toBeLessThanOrEqual(21)
    expect(layout.edges[0].fullLabel).toBe(long)
    expect(layout.width).toBeLessThan(700)
  })

  it('widens the gap between layers to fit an edge label', () => {
    const plain = layoutRelation(nodes('a', 'b'), [edge('a', 'b')])
    const labelled = layoutRelation(nodes('a', 'b'), [edge('a', 'b', 'a fairly long label')])
    expect(labelled.width).toBeGreaterThan(plain.width)
  })

  it('keeps a dense twelve-node graph inside its bounds with no overlapping nodes', () => {
    const ids = 'abcdefghijkl'.split('')
    const links = [
      edge('a', 'c'), edge('b', 'c'), edge('c', 'd'), edge('c', 'e'), edge('d', 'f'), edge('e', 'f'),
      edge('f', 'g'), edge('a', 'g'), edge('g', 'h'), edge('h', 'c'), edge('i', 'j'), edge('j', 'i'),
      edge('b', 'k'), edge('k', 'h'), edge('e', 'l'),
    ]
    const layout = layoutRelation(nodes(...ids), links)
    expect(layout.nodes).toHaveLength(12)
    expect(layout.edges).toHaveLength(links.length)

    layout.nodes.forEach((node, index) => {
      expect(node.x).toBeGreaterThanOrEqual(0)
      expect(node.y).toBeGreaterThanOrEqual(0)
      expect(node.x + node.width).toBeLessThanOrEqual(layout.width)
      expect(node.y + node.height).toBeLessThanOrEqual(layout.height)
      for (const other of layout.nodes.slice(index + 1)) expect(overlaps(node, other)).toBe(false)
    })
    for (const link of layout.edges) expect(link.path).not.toMatch(/NaN|Infinity/)
  })

  it('is deterministic', () => {
    const links = [edge('a', 'b'), edge('b', 'c'), edge('c', 'a'), edge('a', 'd')]
    expect(layoutRelation(nodes('a', 'b', 'c', 'd'), links)).toEqual(layoutRelation(nodes('a', 'b', 'c', 'd'), links))
  })
})
