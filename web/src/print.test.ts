/// <reference types="node" />
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

// Vitest blanks out imported stylesheets, so this one is read from disk.
const css = readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'index.css'), 'utf8')

/** The body of the first top-level block that opens with `opener`. */
function blockOf(source: string, opener: string): string {
  const start = source.indexOf(opener)
  if (start < 0) return ''
  let depth = 0
  for (let i = source.indexOf('{', start); i < source.length; i++) {
    if (source[i] === '{') depth += 1
    if (source[i] === '}' && --depth === 0) return source.slice(start, i + 1)
  }
  return ''
}

describe('print stylesheet', () => {
  it('keeps the dark palette to the screen, so a report always prints light', () => {
    const screenOnly = blockOf(css, '@media screen')
    expect(screenOnly).toContain('[data-theme="dark"]')
    expect(css.replace(screenOnly, '')).not.toContain('[data-theme="dark"]')
  })

  it('prints backgrounds as drawn and leaves a margin around the page', () => {
    const print = blockOf(css, '@media print')
    expect(print).toContain('print-color-adjust: exact')
    expect(print).toContain('@page')
  })
})
