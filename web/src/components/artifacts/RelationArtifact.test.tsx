import { render, screen } from '@testing-library/react'
import type { RelationArtifact as RelationSpec } from '../../types'
import { RelationArtifact } from './RelationArtifact'

const relation = (nodes: unknown, edges: unknown): RelationSpec => ({
  id: 'r',
  type: 'relation',
  title: 'How the datasets join',
  nodes: nodes as RelationSpec['nodes'],
  edges: edges as RelationSpec['edges'],
})

const edgePaths = (container: HTMLElement) => container.querySelectorAll('path[marker-end]')

describe('RelationArtifact', () => {
  it('draws a labelled diagram sized to its content inside a scrollable frame', () => {
    const { container } = render(
      <RelationArtifact
        artifact={relation(
          [{ id: 'a', label: 'Imagery tiles' }, { id: 'b', label: 'Outage reports' }],
          [{ from: 'a', to: 'b', label: 'county + day' }],
        )}
      />,
    )
    const svg = screen.getByRole('img', { name: 'How the datasets join' })
    expect(Number(svg.getAttribute('width'))).toBeGreaterThan(0)
    expect(Number(svg.getAttribute('height'))).toBeGreaterThan(0)
    expect(svg.parentElement).toHaveClass('overflow-x-auto')
    expect(screen.getByText('Imagery tiles')).toBeInTheDocument()
    expect(screen.getByText('Outage reports')).toBeInTheDocument()
    expect(screen.getByText('county + day')).toBeInTheDocument()
    expect(edgePaths(container)).toHaveLength(1)
  })

  it('draws ink-bordered white pills and faint edges', () => {
    const { container } = render(<RelationArtifact artifact={relation([{ id: 'a', label: 'A' }, { id: 'b', label: 'B' }], [{ from: 'a', to: 'b' }])} />)
    const pill = container.querySelector('rect')!
    expect(pill).toHaveAttribute('fill', 'var(--color-paper)')
    expect(pill).toHaveAttribute('stroke', 'var(--color-ink)')
    expect(edgePaths(container)[0]).toHaveAttribute('stroke', 'var(--color-faint)')
  })

  it('sets edge labels in muted mono on a white knockout wide enough for the text', () => {
    render(<RelationArtifact artifact={relation([{ id: 'a', label: 'A' }, { id: 'b', label: 'B' }], [{ from: 'a', to: 'b', label: 'county + day' }])} />)
    const label = screen.getByText('county + day')
    expect(label).toHaveClass('font-mono')
    expect(label).toHaveAttribute('fill', 'var(--color-muted)')
    const knockout = label.previousElementSibling!
    expect(knockout).toHaveAttribute('fill', 'var(--color-paper)')
    expect(Number(knockout.getAttribute('width'))).toBeGreaterThan('county + day'.length * 6.6)
  })

  it('gives each diagram its own arrowhead marker', () => {
    const spec = relation([{ id: 'a', label: 'A' }, { id: 'b', label: 'B' }], [{ from: 'a', to: 'b' }])
    const { container } = render(
      <>
        <RelationArtifact artifact={spec} />
        <RelationArtifact artifact={spec} />
      </>,
    )
    const ids = [...container.querySelectorAll('marker')].map((marker) => marker.id)
    expect(new Set(ids).size).toBe(2)
    edgePaths(container).forEach((path, index) => expect(path.getAttribute('marker-end')).toBe(`url(#${ids[index]})`))
  })

  it('survives cycles, self-loops, duplicate ids and edges to missing nodes', () => {
    const { container } = render(
      <RelationArtifact
        artifact={relation(
          [{ id: 'a', label: 'A' }, { id: 'a', label: 'Again' }, { id: 'b', label: 'B' }, { id: 'c', label: 'C' }],
          [
            { from: 'a', to: 'b' },
            { from: 'b', to: 'c' },
            { from: 'c', to: 'a' },
            { from: 'a', to: 'a' },
            { from: 'a', to: 'ghost' },
          ],
        )}
      />,
    )
    expect(screen.queryByText('Again')).not.toBeInTheDocument()
    expect(edgePaths(container)).toHaveLength(3)
  })

  it('truncates long labels and keeps the full text as a tooltip', () => {
    const long = 'A very long dataset name that goes on and on and on'
    const { container } = render(<RelationArtifact artifact={relation([{ id: 'a', label: long }], [])} />)
    expect(screen.queryByText(long, { selector: 'text' })).not.toBeInTheDocument()
    expect(container.querySelector('title')).toHaveTextContent(long)
  })

  it('renders nodes without edges', () => {
    const { container } = render(<RelationArtifact artifact={relation([{ id: 'a', label: 'Alone' }], undefined)} />)
    expect(screen.getByText('Alone')).toBeInTheDocument()
    expect(edgePaths(container)).toHaveLength(0)
  })

  it.each([[[]], [undefined], [[null, {}]]])('shows a quiet empty state for nodes %j', (nodes) => {
    render(<RelationArtifact artifact={relation(nodes, [{ from: 'a', to: 'b' }])} />)
    expect(screen.getByText('Nothing to show')).toBeInTheDocument()
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })
})
