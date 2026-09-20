export interface GraphNode {
  id: string
  label: string
}

export interface GraphEdge {
  from: string
  to: string
  label?: string
}

/** An edge oriented for layout: always points from an earlier layer to a later one. */
export interface Link {
  src: string
  dst: string
  edge: GraphEdge
  reversed: boolean
}

// The spec allows 12 nodes; the cap only keeps a runaway payload from producing an unreadable, slow figure.
const MAX_NODES = 24

const text = (value: unknown) => (typeof value === 'string' ? value.trim() : typeof value === 'number' ? String(value) : '')

/** Drops junk, duplicate ids, self-loops, repeated edges and edges to nodes that do not exist. */
export function cleanGraph(rawNodes: unknown, rawEdges: unknown): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const nodes = new Map<string, GraphNode>()
  for (const raw of Array.isArray(rawNodes) ? rawNodes : []) {
    const id = text(raw?.id)
    if (id && !nodes.has(id) && nodes.size < MAX_NODES) nodes.set(id, { id, label: text(raw.label) || id })
  }
  const edges = new Map<string, GraphEdge>()
  for (const raw of Array.isArray(rawEdges) ? rawEdges : []) {
    const from = text(raw?.from)
    const to = text(raw?.to)
    const key = JSON.stringify([from, to])
    if (from !== to && nodes.has(from) && nodes.has(to) && !edges.has(key)) {
      edges.set(key, { from, to, label: text(raw.label) || undefined })
    }
  }
  return { nodes: [...nodes.values()], edges: [...edges.values()] }
}

/** Reverses the back-edges a depth-first walk finds (in node, then edge, order) so the result is acyclic. */
export function orientEdges(nodes: GraphNode[], edges: GraphEdge[]): Link[] {
  const outgoing = new Map<string, GraphEdge[]>(nodes.map((node) => [node.id, []]))
  for (const edge of edges) outgoing.get(edge.from)!.push(edge)

  const state = new Map<string, 'open' | 'done'>()
  const back = new Set<GraphEdge>()
  const visit = (id: string) => {
    state.set(id, 'open')
    for (const edge of outgoing.get(id)!) {
      if (state.get(edge.to) === 'open') back.add(edge)
      else if (!state.has(edge.to)) visit(edge.to)
    }
    state.set(id, 'done')
  }
  for (const node of nodes) if (!state.has(node.id)) visit(node.id)

  return edges.map((edge) =>
    back.has(edge) ? { src: edge.to, dst: edge.from, edge, reversed: true } : { src: edge.from, dst: edge.to, edge, reversed: false },
  )
}

/** Longest-path layering: a node sits one layer past its deepest parent. */
export function assignLayers(nodes: GraphNode[], links: Link[]): Map<string, number> {
  const parents = new Map<string, string[]>(nodes.map((node) => [node.id, []]))
  for (const link of links) parents.get(link.dst)!.push(link.src)

  const layers = new Map<string, number>()
  const layerOf = (id: string): number => {
    if (!layers.has(id)) layers.set(id, Math.max(-1, ...parents.get(id)!.map(layerOf)) + 1)
    return layers.get(id)!
  }
  for (const node of nodes) layerOf(node.id)
  return layers
}
