import { assignLayers, cleanGraph, orientEdges, type Link } from './relationGraph'
import { truncate } from './text'

export interface PlacedNode {
  id: string
  label: string
  fullLabel: string
  layer: number
  x: number
  y: number
  width: number
  height: number
}

export interface PlacedEdge {
  key: string
  from: string
  to: string
  path: string
  label?: string
  fullLabel?: string
  labelX: number
  labelY: number
}

export interface RelationLayout {
  width: number
  height: number
  nodes: PlacedNode[]
  edges: PlacedEdge[]
}

const NODE_HEIGHT = 28
const NODE_PAD_X = 13
const NODE_CHAR = 6.6
/** Advance width of 11px Geist Mono. */
export const LABEL_CHAR = 6.6
const ROW_GAP = 20
const LAYER_GAP = 56
const LABEL_MARGIN = 20
const CROSSING_WEIGHT = 0.001
const LABEL_SHIFT = 0.15
const ARROW_GAP = 2
const BACK_EDGE_DROP = 6
const MARGIN = 1
const MAX_NODE_LABEL = 26
const MAX_EDGE_LABEL = 20

/** A node, or the point where a long edge crosses a layer it skips. */
interface Item {
  id: string
  layer: number
  width: number
  height: number
  centerY: number
  /** How strongly the item holds its row: long edges give way to nodes so chains stay straight. */
  weight: number
}

const bezier = (p0: number, p1: number, p2: number, p3: number, t: number) =>
  (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3
const mean = (values: number[]) => values.reduce((sum, value) => sum + value, 0) / values.length

function orderLayers(layers: Item[][], chains: string[][]) {
  const before = new Map<string, string[]>()
  const after = new Map<string, string[]>()
  const push = (map: Map<string, string[]>, key: string, value: string) => map.set(key, [...(map.get(key) ?? []), value])
  for (const chain of chains) {
    chain.slice(1).forEach((id, index) => {
      push(before, id, chain[index])
      push(after, chain[index], id)
    })
  }

  const rank = new Map<string, number>()
  const index = (layer: Item[]) => layer.forEach((item, position) => rank.set(item.id, position))
  layers.forEach(index)

  // Barycentre sweeps: each layer follows the average position of its neighbours in the layer just settled.
  const settle = (layer: Item[], neighbours: Map<string, string[]>) => {
    const score = (item: Item) => {
      const linked = neighbours.get(item.id)
      return linked ? mean(linked.map((id) => rank.get(id)!)) : rank.get(item.id)!
    }
    const scores = new Map(layer.map((item) => [item.id, score(item)]))
    layer.sort((a, b) => scores.get(a.id)! - scores.get(b.id)! || rank.get(a.id)! - rank.get(b.id)!)
    index(layer)
  }
  for (const layer of layers.slice(1)) settle(layer, before)
  for (const layer of layers.slice(0, -1).reverse()) settle(layer, after)
  for (const layer of layers.slice(1)) settle(layer, before)
  return { parents: before, children: after }
}

const spacing = (above: Item, below: Item) => (above.height + below.height) / 2 + ROW_GAP

/** Items that would overlap, moved as one so their order and spacing hold. */
interface Block {
  items: Item[]
  /** Distance of each item's centre below the first item's centre. */
  offsets: number[]
  weight: number
  /** Weighted sum of where each item would put the block's first centre. */
  pull: number
}

const blockTop = (block: Block) => block.pull / block.weight
const lastOf = <T,>(values: T[]) => values[values.length - 1]

/** Puts every item as close to where it wants to be as the row spacing allows. */
function placeLayer(layer: Item[], wanted: number[]) {
  const blocks: Block[] = []
  layer.forEach((item, position) => {
    let block: Block = { items: [item], offsets: [0], weight: item.weight, pull: item.weight * wanted[position] }
    for (let above = lastOf(blocks); above; above = lastOf(blocks)) {
      const shift = lastOf(above.offsets) + spacing(lastOf(above.items), block.items[0])
      if (blockTop(above) + shift <= blockTop(block)) break
      blocks.pop()
      block = {
        items: [...above.items, ...block.items],
        offsets: [...above.offsets, ...block.offsets.map((offset) => offset + shift)],
        weight: above.weight + block.weight,
        pull: above.pull + block.pull - block.weight * shift,
      }
    }
    blocks.push(block)
  })
  for (const block of blocks) {
    block.items.forEach((item, position) => (item.centerY = Math.round(blockTop(block) + block.offsets[position])))
  }
}

function placeRows(layers: Item[][], parents: Map<string, string[]>, children: Map<string, string[]>, items: Map<string, Item>) {
  const follow = (layer: Item[], neighbours: Map<string, string[]>) => {
    const wanted = layer.map((item) => {
      const linked = (neighbours.get(item.id) ?? []).map((id) => items.get(id)!)
      const weight = linked.reduce((sum, other) => sum + other.weight, 0)
      return weight ? linked.reduce((sum, other) => sum + other.weight * other.centerY, 0) / weight : item.centerY
    })
    placeLayer(layer, wanted)
  }
  // Down, up, down: children line up with parents, parents recentre on their children, then children settle.
  for (const layer of layers) follow(layer, parents)
  for (const layer of layers.slice(0, -1).reverse()) follow(layer, children)
  for (const layer of layers.slice(1)) follow(layer, parents)
}

function edgePath(points: { x: number; y: number }[]) {
  return points
    .map(({ x, y }, position) => {
      if (position === 0) return `M ${x} ${y}`
      if (position % 2 === 0) return `L ${x} ${y}`
      const from = points[position - 1]
      const middle = (from.x + x) / 2
      return `C ${middle} ${from.y} ${middle} ${y} ${x} ${y}`
    })
    .join(' ')
}

export function layoutRelation(rawNodes: unknown, rawEdges: unknown): RelationLayout {
  const graph = cleanGraph(rawNodes, rawEdges)
  if (graph.nodes.length === 0) return { width: 0, height: 0, nodes: [], edges: [] }

  const links = orientEdges(graph.nodes, graph.edges)
  const layerOf = assignLayers(graph.nodes, links)
  const layers: Item[][] = Array.from({ length: Math.max(...layerOf.values()) + 1 }, () => [])
  const items = new Map<string, Item>()
  const add = (item: Item) => {
    items.set(item.id, item)
    layers[item.layer].push(item)
    return item.id
  }

  const labels = new Map(graph.nodes.map((node) => [node.id, truncate(node.label, MAX_NODE_LABEL)]))
  for (const node of graph.nodes) {
    const width = Math.round(labels.get(node.id)!.length * NODE_CHAR) + NODE_PAD_X * 2
    add({ id: node.id, layer: layerOf.get(node.id)!, width, height: NODE_HEIGHT, centerY: 0, weight: 1 })
  }

  const chainOf = (link: Link, position: number) => {
    const first = layerOf.get(link.src)!
    const skipped = Math.max(0, layerOf.get(link.dst)! - first - 1)
    // Node ids are trimmed, so an id with a leading space can never collide with one.
    const crossings = Array.from({ length: skipped }, (_, step) =>
      add({ id: ` ${position}:${step}`, layer: first + step + 1, width: 0, height: 0, centerY: 0, weight: CROSSING_WEIGHT }),
    )
    return [link.src, ...crossings, link.dst]
  }
  const chains = links.map(chainOf)

  const { parents, children } = orderLayers(layers, chains)
  placeRows(layers, parents, children, items)

  const edgeLabels = links.map((link) => (link.edge.label ? truncate(link.edge.label, MAX_EDGE_LABEL) : undefined))
  // Edges bunch up where they share a node, so a label sits toward the end of its edge that has the fewest neighbours.
  const fan = (id: string, end: 'src' | 'dst') => links.filter((link) => link[end] === id).length
  const labelAt = links.map((link) => Math.sign(fan(link.src, 'src') - fan(link.dst, 'dst')) * LABEL_SHIFT + 0.5)
  const columns: { x: number; width: number }[] = []
  layers.forEach((layer, position) => {
    const previous = columns[position - 1]
    const labelRoom = links.map((link, at) => {
      const label = edgeLabels[at]
      if (!label || layerOf.get(link.src) !== position - 1) return 0
      const along = bezier(0, 0.5, 0.5, 1, labelAt[at])
      return ((label.length * LABEL_CHAR) / 2 + LABEL_MARGIN) / Math.min(along, 1 - along)
    })
    const gap = Math.round(Math.max(LAYER_GAP, ...labelRoom))
    columns.push({ x: previous ? previous.x + previous.width + gap : MARGIN, width: Math.max(...layer.map((item) => item.width)) })
  })

  const top = Math.min(...[...items.values()].map((item) => item.centerY - item.height / 2))
  for (const item of items.values()) item.centerY += MARGIN - top

  const left = (item: Item) => columns[item.layer].x + (columns[item.layer].width - item.width) / 2
  const nodes = graph.nodes.map((node): PlacedNode => {
    const item = items.get(node.id)!
    return {
      id: node.id,
      label: labels.get(node.id)!,
      fullLabel: node.label,
      layer: item.layer,
      x: left(item),
      y: item.centerY - item.height / 2,
      width: item.width,
      height: item.height,
    }
  })

  const edges = links.map((link, position): PlacedEdge => {
    const chain = chains[position].map((id) => items.get(id)!)
    const source = chain[0]
    const target = chain[chain.length - 1]
    const points = [
      { x: left(source) + source.width, y: source.centerY },
      ...chain.slice(1, -1).flatMap((crossing) => {
        const column = columns[crossing.layer]
        return [
          { x: column.x, y: crossing.centerY },
          { x: column.x + column.width, y: crossing.centerY },
        ]
      }),
      { x: left(target), y: target.centerY },
    ]
    const [from, to] = points
    const middle = (from.x + to.x) / 2
    const labelX = bezier(from.x, middle, middle, to.x, labelAt[position])
    const labelY = bezier(from.y, from.y, to.y, to.y, labelAt[position])

    if (link.reversed) {
      // A back-edge often runs alongside a forward one; attaching it lower keeps the two arrowheads apart.
      points.reverse()
      points[0].y += BACK_EDGE_DROP
      points[points.length - 1].y += BACK_EDGE_DROP
    }
    points[points.length - 1].x += link.reversed ? ARROW_GAP : -ARROW_GAP

    return {
      key: String(position),
      from: link.edge.from,
      to: link.edge.to,
      path: edgePath(points),
      label: edgeLabels[position],
      fullLabel: link.edge.label,
      labelX,
      labelY,
    }
  })

  return {
    width: columns[columns.length - 1].x + columns[columns.length - 1].width + MARGIN,
    height: Math.max(...[...items.values()].map((item) => item.centerY + item.height / 2)) + MARGIN,
    nodes,
    edges,
  }
}
