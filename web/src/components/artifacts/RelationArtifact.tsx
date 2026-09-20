import { useId, useMemo } from 'react'
import type { RelationArtifact as RelationSpec } from '../../types'
import { EmptyBody } from './EmptyBody'
import { LABEL_CHAR, layoutRelation } from './relationLayout'
import { asText } from './text'

const INK = 'var(--color-ink)'
const MUTED = 'var(--color-muted)'
const FAINT = 'var(--color-faint)'
// Theme tokens rather than hex, so the diagram turns over with dark mode.
const PAPER = 'var(--color-paper)'
const KNOCKOUT_PAD = 5

export function RelationArtifact({ artifact }: { artifact: RelationSpec }) {
  const markerId = useId()
  const layout = useMemo(() => layoutRelation(artifact.nodes, artifact.edges), [artifact.nodes, artifact.edges])
  if (layout.nodes.length === 0) return <EmptyBody />

  return (
    <div className="overflow-x-auto py-2">
      <svg
        role="img"
        aria-label={asText(artifact.title) || 'Relation diagram'}
        width={layout.width}
        height={layout.height}
        viewBox={`0 0 ${layout.width} ${layout.height}`}
        className="mx-auto block max-w-none"
      >
        <defs>
          <marker id={markerId} viewBox="0 0 6 6" markerWidth="6" markerHeight="6" refX="5.5" refY="3" orient="auto" markerUnits="userSpaceOnUse">
            <path d="M 0 0.5 L 5.5 3 L 0 5.5 Z" fill={FAINT} />
          </marker>
        </defs>
        {layout.edges.map((edge) => (
          <path key={edge.key} d={edge.path} fill="none" stroke={FAINT} strokeWidth="1" markerEnd={`url(#${markerId})`} />
        ))}
        {layout.edges.map(
          (edge) =>
            edge.label && (
              <g key={edge.key}>
                {edge.fullLabel !== edge.label && <title>{edge.fullLabel}</title>}
                <rect
                  x={edge.labelX - (edge.label.length * LABEL_CHAR) / 2 - KNOCKOUT_PAD}
                  y={edge.labelY - 8}
                  width={edge.label.length * LABEL_CHAR + KNOCKOUT_PAD * 2}
                  height="16"
                  fill={PAPER}
                />
                <text x={edge.labelX} y={edge.labelY} textAnchor="middle" dominantBaseline="central" fontSize="11" fill={MUTED} className="font-mono">
                  {edge.label}
                </text>
              </g>
            ),
        )}
        {layout.nodes.map((node) => (
          <g key={node.id}>
            {node.fullLabel !== node.label && <title>{node.fullLabel}</title>}
            <rect x={node.x} y={node.y} width={node.width} height={node.height} rx={node.height / 2} fill={PAPER} stroke={INK} strokeWidth="1" />
            <text x={node.x + node.width / 2} y={node.y + node.height / 2} textAnchor="middle" dominantBaseline="central" fontSize="12" fill={INK}>
              {node.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  )
}
