import { render } from '@testing-library/react'
import type { DatasetKind } from '../types'
import { DatasetThumbnail } from './DatasetThumbnail'

const KINDS: DatasetKind[] = ['events', 'markets', 'weather', 'air', 'other']
const PALETTE = ['#0a0a0a', '#bdbdbd', '#e5e5e5', 'none']

const markup = (id: string, kind: DatasetKind) => render(<DatasetThumbnail id={id} kind={kind} />).container.innerHTML

describe('DatasetThumbnail', () => {
  it.each(KINDS)('draws a decorative svg for %s', (kind) => {
    const { container } = render(<DatasetThumbnail id="gdelt" kind={kind} />)
    const svg = container.querySelector('svg')
    expect(svg).toHaveAttribute('aria-hidden', 'true')
    expect(svg?.querySelectorAll('path, circle, line').length).toBeGreaterThan(0)
  })

  it.each(KINDS)('is deterministic for the same id (%s)', (kind) => {
    expect(markup('gdelt', kind)).toBe(markup('gdelt', kind))
  })

  it.each(KINDS)('differs between two ids of the same kind (%s)', (kind) => {
    expect(markup('d-1', kind)).not.toBe(markup('d-2', kind))
  })

  it('draws each kind differently', () => {
    expect(new Set(KINDS.map((kind) => markup('gdelt', kind))).size).toBe(KINDS.length)
  })

  it.each(KINDS)('stays inside the palette, with no gradients or images (%s)', (kind) => {
    const { container } = render(<DatasetThumbnail id="gdelt" kind={kind} />)
    expect(container.querySelector('linearGradient, radialGradient, image, filter')).toBeNull()
    container.querySelectorAll('[stroke], [fill]').forEach((node) => {
      for (const attribute of ['stroke', 'fill']) {
        const value = node.getAttribute(attribute)
        if (value !== null) expect(PALETTE).toContain(value)
      }
    })
  })

  it.each(KINDS)('emits only finite coordinates (%s)', (kind) => {
    expect(markup('', kind)).not.toMatch(/NaN|Infinity|undefined/)
  })
})
