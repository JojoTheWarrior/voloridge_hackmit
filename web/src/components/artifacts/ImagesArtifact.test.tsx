import { fireEvent, render, screen } from '@testing-library/react'
import type { ImagesArtifact as ImagesSpec } from '../../types'
import { ImagesArtifact } from './ImagesArtifact'

const images = (items: unknown): ImagesSpec => ({ id: 'i', type: 'images', title: 'Images', items: items as ImagesSpec['items'] })

describe('ImagesArtifact', () => {
  it('renders lazy images with alt text from the caption', () => {
    render(<ImagesArtifact artifact={images([{ src: 'https://example.com/a.png', caption: 'Flooded street' }, { src: '/api/missions/m1/attachments/b.png' }])} />)
    const [first, second] = screen.getAllByRole('img')
    expect(first).toHaveAttribute('src', 'https://example.com/a.png')
    expect(first).toHaveAttribute('alt', 'Flooded street')
    expect(first).toHaveAttribute('loading', 'lazy')
    expect(second).toHaveAttribute('alt', 'Image 2')
    expect(screen.getByText('Flooded street').tagName).toBe('FIGCAPTION')
  })

  it('is two across on phones and up to four across on larger screens', () => {
    const items = Array.from({ length: 5 }, (_, index) => ({ src: `https://example.com/${index}.png` }))
    const { container } = render(<ImagesArtifact artifact={images(items)} />)
    expect(container.firstElementChild).toHaveClass('grid', 'grid-cols-2', 'sm:grid-cols-4')
  })

  it('uses fewer, larger columns when there are only a few images', () => {
    const { container } = render(<ImagesArtifact artifact={images([{ src: 'https://example.com/a.png' }, { src: 'https://example.com/b.png' }, { src: 'https://example.com/c.png' }])} />)
    expect(container.firstElementChild).toHaveClass('sm:grid-cols-3')
  })

  it('shows a fill placeholder until the image loads, then fades it in', () => {
    render(<ImagesArtifact artifact={images([{ src: 'https://example.com/a.png', caption: 'A' }])} />)
    const img = screen.getByRole('img')
    expect(img.parentElement).toHaveClass('bg-fill')
    expect(img).toHaveClass('opacity-0')
    fireEvent.load(img)
    expect(img).toHaveClass('opacity-100')
  })

  it('collapses a broken image to a muted tile', () => {
    render(<ImagesArtifact artifact={images([{ src: 'https://example.com/a.png', caption: 'A' }])} />)
    fireEvent.error(screen.getByRole('img'))
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
    expect(screen.getByText('Image unavailable')).toBeInTheDocument()
    expect(screen.getByText('A')).toBeInTheDocument()
  })

  it.each([[''], ['javascript:alert(1)'], ['attachment:unresolved.png'], [undefined], [42]])(
    'treats the unusable src %j as unavailable without requesting it',
    (src) => {
      render(<ImagesArtifact artifact={images([{ src }])} />)
      expect(screen.queryByRole('img')).not.toBeInTheDocument()
      expect(screen.getByText('Image unavailable')).toBeInTheDocument()
    },
  )

  it('keeps duplicate sources and truncates long captions with the full text on hover', () => {
    const long = 'caption '.repeat(60).trim()
    render(<ImagesArtifact artifact={images([{ src: 'https://example.com/a.png', caption: long }, { src: 'https://example.com/a.png' }])} />)
    expect(screen.getAllByRole('img')).toHaveLength(2)
    expect(screen.getByText(long)).toHaveClass('truncate')
    expect(screen.getByText(long)).toHaveAttribute('title', long)
  })

  it('skips junk items', () => {
    render(<ImagesArtifact artifact={images([null, 'junk', { src: 'https://example.com/a.png' }])} />)
    expect(screen.getAllByRole('img')).toHaveLength(1)
  })

  it.each([[[]], [undefined], [[null]]])('shows a quiet empty state for %j', (items) => {
    render(<ImagesArtifact artifact={images(items)} />)
    expect(screen.getByText('Nothing to show')).toBeInTheDocument()
  })
})
