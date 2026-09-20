import { render, screen } from '@testing-library/react'
import type { StatsArtifact as StatsSpec } from '../../types'
import { StatsArtifact } from './StatsArtifact'

const stats = (items: unknown): StatsSpec => ({ id: 's', type: 'stats', title: 'Stats', items: items as StatsSpec['items'] })

describe('StatsArtifact', () => {
  it('renders each label with its value in mono', () => {
    render(<StatsArtifact artifact={stats([{ label: 'Correlation', value: '0.58' }, { label: 'n', value: '412' }])} />)
    expect(screen.getByText('Correlation').tagName).toBe('DT')
    const value = screen.getByText('0.58')
    expect(value.tagName).toBe('DD')
    expect(value).toHaveClass('font-mono')
    expect(screen.getByText('412')).toBeInTheDocument()
  })

  it('keeps duplicate labels and clamps absurd values with the full text on hover', () => {
    const long = '9'.repeat(300)
    render(<StatsArtifact artifact={stats([{ label: 'Same', value: '1' }, { label: 'Same', value: long }])} />)
    expect(screen.getAllByText('Same')).toHaveLength(2)
    const value = screen.getByText(long)
    expect(value).toHaveClass('line-clamp-3')
    expect(value).toHaveAttribute('title', long)
  })

  it('coerces non-string values and skips junk entries', () => {
    render(<StatsArtifact artifact={stats([{ label: 'n', value: 412 }, null, 'junk', { label: 'Lag' }])} />)
    expect(screen.getByText('412')).toBeInTheDocument()
    expect(screen.getByText('Lag')).toBeInTheDocument()
    expect(screen.getByText('—')).toBeInTheDocument()
    expect(screen.getAllByRole('term')).toHaveLength(2)
  })

  it.each([[[]], [undefined], ['junk']])('shows a quiet empty state for %j', (items) => {
    render(<StatsArtifact artifact={stats(items)} />)
    expect(screen.getByText('Nothing to show')).toBeInTheDocument()
  })

  it('sets a short value large and a sentence-length value small enough to read in full', () => {
    render(
      <StatsArtifact
        artifact={stats([
          { label: 'r', value: '0.58' },
          { label: 'Granger', value: 'p = 0.52 / 0.85 / 0.63 / 0.38 / 0.13 (all null)' },
          { label: 'Edge', value: '1234567890123456' },
        ])}
      />,
    )
    expect(screen.getByText('0.58')).toHaveClass('text-lg', 'truncate')
    expect(screen.getByText('1234567890123456')).toHaveClass('text-lg')
    const long = screen.getByText('p = 0.52 / 0.85 / 0.63 / 0.38 / 0.13 (all null)')
    expect(long).toHaveClass('text-[13px]', 'break-words')
    expect(long).not.toHaveClass('truncate')
  })
})
