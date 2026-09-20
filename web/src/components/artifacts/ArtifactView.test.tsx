import { render, screen } from '@testing-library/react'
import type { Artifact } from '../../types'
import { ArtifactView } from './ArtifactView'

const stats: Artifact = { id: 'a', type: 'stats', title: 'Core stats', items: [{ label: 'n', value: '412' }] }

describe('ArtifactView', () => {
  it('frames the artifact as a hairline figure with its title', () => {
    render(<ArtifactView artifact={stats} />)
    const figure = screen.getByRole('figure', { name: 'Core stats' })
    expect(figure).toHaveClass('fade-in', 'rounded-xl', 'border', 'border-line', 'p-5')
    expect(screen.getByRole('heading', { name: 'Core stats' })).toBeInTheDocument()
    expect(screen.getByText('412')).toBeInTheDocument()
  })

  it('shows the caption beneath when present and nothing otherwise', () => {
    const { rerender, container } = render(<ArtifactView artifact={{ ...stats, caption: 'Across 412 counties.' }} />)
    expect(screen.getByText('Across 412 counties.').tagName).toBe('FIGCAPTION')
    rerender(<ArtifactView artifact={stats} />)
    expect(container.querySelector('figcaption')).toBeNull()
  })

  it('shows a chart headline in mono beside the title', () => {
    render(<ArtifactView artifact={{ id: 'c', type: 'chart', kind: 'scatter', title: 'Share vs hours', headline: 'r = 0.58', series: [] }} />)
    expect(screen.getByText('r = 0.58')).toHaveClass('font-mono')
  })

  it('clamps an absurd title to two lines and truncates the headline, keeping the full text on hover', () => {
    const long = 'title '.repeat(80).trim()
    render(<ArtifactView artifact={{ id: 'c', type: 'chart', kind: 'line', title: long, headline: long, series: [] }} />)
    expect(screen.getByRole('heading')).toHaveAttribute('title', long)
    expect(screen.getByRole('heading')).toHaveClass('line-clamp-2')
    expect(screen.getByText(long, { selector: 'span' })).toHaveClass('truncate')
    expect(screen.getAllByTitle(long)).toHaveLength(2)
  })

  it.each<[Artifact['type'], Artifact, string]>([
    ['chart', { id: '1', type: 'chart', kind: 'line', title: 'T', series: [] }, 'Nothing to show'],
    ['images', { id: '2', type: 'images', title: 'T', items: [{ src: '' }] }, 'Image unavailable'],
    ['relation', { id: '3', type: 'relation', title: 'T', nodes: [{ id: 'a', label: 'Node A' }], edges: [] }, 'Node A'],
    ['table', { id: '4', type: 'table', title: 'T', columns: ['Col'], rows: [['cell']] }, 'cell'],
    ['stats', stats, '412'],
    ['image', { id: '6', type: 'image', title: 'T', src: '' }, 'Image unavailable'],
  ])('renders the %s renderer', (_, artifact, text) => {
    render(<ArtifactView artifact={artifact} />)
    expect(screen.getByText(text)).toBeInTheDocument()
  })

  it('renders nothing for an unknown type or a missing artifact', () => {
    const { container, rerender } = render(<ArtifactView artifact={{ id: 'x', type: 'hologram', title: 'T' } as unknown as Artifact} />)
    expect(container).toBeEmptyDOMElement()
    rerender(<ArtifactView artifact={null as unknown as Artifact} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('falls back to a plain label when the title is missing', () => {
    render(<ArtifactView artifact={{ ...stats, title: undefined as unknown as string }} />)
    expect(screen.getByRole('figure', { name: 'Untitled' })).toBeInTheDocument()
  })
})
