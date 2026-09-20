import type { TableArtifact as TableSpec } from '../../types'
import { EmptyBody } from './EmptyBody'
import { asText } from './text'

// Plain numbers plus the decorations analysts add: signs, currency, separators, %, a short unit, "<0.001".
const NUMERIC = /^[<>≤≥~]?\s?[-−+]?[$€£]?\d[\d,]*(\.\d+)?(e[-+]?\d+)?\s?(%|[a-zA-Zµ]{1,3})?$/

const isNumeric = (cell: string) => NUMERIC.test(cell.trim())

export function TableArtifact({ artifact }: { artifact: TableSpec }) {
  const columns = (Array.isArray(artifact.columns) ? artifact.columns : []).map(asText)
  const rawRows = (Array.isArray(artifact.rows) ? artifact.rows : []).filter(Array.isArray)
  const width = columns.length || Math.max(0, ...rawRows.map((row) => row.length))
  if (width === 0 || rawRows.length === 0) return <EmptyBody />

  const rows = rawRows.map((row) => Array.from({ length: width }, (_, index) => asText(row[index])))
  // Alignment is decided per column so figures line up; the first column names the row and stays left.
  const numeric = Array.from({ length: width }, (_, index) => {
    const cells = rows.map((row) => row[index]).filter((cell) => cell.trim() !== '' && cell !== '—')
    return index > 0 && cells.length > 0 && cells.every(isNumeric)
  })

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm whitespace-nowrap">
        {columns.length > 0 && (
          <thead>
            <tr className="border-b border-line-soft text-xs text-muted">
              {columns.map((column, index) => (
                <th
                  key={index}
                  scope="col"
                  title={column}
                  className={`max-w-[11rem] truncate pb-2.5 font-normal sm:max-w-[16rem] ${index > 0 ? 'pl-4 sm:pl-6' : ''} ${numeric[index] ? 'text-right' : ''}`}
                >
                  {column}
                </th>
              ))}
            </tr>
          </thead>
        )}
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex} className="group border-b border-line-soft last:border-0">
              {row.map((cell, index) => (
                <td
                  key={index}
                  title={cell}
                  className={`max-w-[11rem] truncate py-3 group-last:pb-1 sm:max-w-[16rem] ${index > 0 ? 'pl-4 sm:pl-6' : ''} ${
                    index === 0 ? 'text-ink' : numeric[index] ? 'text-right font-mono text-[13px]' : 'text-muted'
                  }`}
                >
                  {numeric[index] ? cell.replace(/^([<>≤≥~]?\s?)-/, '$1−') : cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
