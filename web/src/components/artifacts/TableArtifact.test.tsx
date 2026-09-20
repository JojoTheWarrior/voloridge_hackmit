import { render, screen, within } from '@testing-library/react'
import type { TableArtifact as TableSpec } from '../../types'
import { TableArtifact } from './TableArtifact'

const table = (columns: unknown, rows: unknown): TableSpec => ({
  id: 't',
  type: 'table',
  title: 'Table',
  columns: columns as string[],
  rows: rows as string[][],
})

const cellsOf = (row: HTMLElement) => within(row).getAllByRole('cell').map((cell) => cell.textContent)

describe('TableArtifact', () => {
  it('renders headers and rows', () => {
    render(<TableArtifact artifact={table(['County', 'Hours'], [['Harris', '9.1'], ['Travis', '4.2']])} />)
    expect(screen.getAllByRole('columnheader').map((th) => th.textContent)).toEqual(['County', 'Hours'])
    const [, first, second] = screen.getAllByRole('row')
    expect(cellsOf(first)).toEqual(['Harris', '9.1'])
    expect(cellsOf(second)).toEqual(['Travis', '4.2'])
  })

  it('right-aligns numeric columns in mono, header included, and leaves text columns alone', () => {
    render(
      <TableArtifact
        artifact={table(['Name', 'r', 'Share', 'p', 'Note'], [['A', '-0.58', '12%', '<0.001', 'ok'], ['B', '1,204', '', '0.2', '3 of 4']])}
      />,
    )
    for (const text of ['−0.58', '1,204', '12%', '<0.001']) {
      expect(screen.getByText(text)).toHaveClass('text-right', 'font-mono')
    }
    expect(screen.getByRole('columnheader', { name: 'r' })).toHaveClass('text-right')
    expect(screen.getByRole('columnheader', { name: 'Note' })).not.toHaveClass('text-right')
    expect(screen.getByText('3 of 4')).not.toHaveClass('font-mono')
  })

  it('never treats the first column as numeric so row names stay ink on the left', () => {
    render(<TableArtifact artifact={table(['Year', 'Value'], [['2024', '1'], ['2025', '2']])} />)
    expect(screen.getByText('2024')).not.toHaveClass('text-right')
    expect(screen.getByText('2024')).toHaveClass('text-ink')
  })

  it('pads short rows and trims long ones to the column count', () => {
    render(<TableArtifact artifact={table(['A', 'B', 'C'], [['1'], ['1', '2', '3', '4', '5']])} />)
    const [, short, long] = screen.getAllByRole('row')
    expect(cellsOf(short)).toEqual(['1', '', ''])
    expect(cellsOf(long)).toEqual(['1', '2', '3'])
  })

  it('renders rows without a header when there are no columns', () => {
    render(<TableArtifact artifact={table([], [['a', 'b'], ['c']])} />)
    expect(screen.queryAllByRole('columnheader')).toHaveLength(0)
    expect(screen.getAllByRole('row').map(cellsOf)).toEqual([['a', 'b'], ['c', '']])
  })

  it('coerces non-string cells and skips rows that are not arrays', () => {
    render(<TableArtifact artifact={table(['A', 'B'], [[1, null], 'junk', null, [true, { x: 1 }]])} />)
    const rows = screen.getAllByRole('row').slice(1)
    expect(rows).toHaveLength(2)
    expect(cellsOf(rows[0])).toEqual(['1', ''])
    expect(cellsOf(rows[1])[0]).toBe('true')
  })

  it('truncates absurdly long cells and headers with the full text on hover', () => {
    const long = 'word '.repeat(100).trim()
    render(<TableArtifact artifact={table([long, 'B'], [[long, 'x']])} />)
    const [header, cell] = screen.getAllByTitle(long)
    expect(header).toHaveClass('truncate')
    expect(cell).toHaveClass('truncate')
  })

  it('scrolls inside its own frame rather than widening the page', () => {
    const { container } = render(<TableArtifact artifact={table(['A'], [['1']])} />)
    expect(container.firstElementChild).toHaveClass('overflow-x-auto')
  })

  it.each([
    ['no rows', ['A'], []],
    ['nothing at all', [], []],
    ['only empty rows', [], [[], []]],
    ['missing fields', undefined, undefined],
  ])('shows a quiet empty state for %s', (_, columns, rows) => {
    render(<TableArtifact artifact={table(columns, rows)} />)
    expect(screen.getByText('Nothing to show')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })
})
