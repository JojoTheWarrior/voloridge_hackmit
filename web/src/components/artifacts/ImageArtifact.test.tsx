import { fireEvent, render, screen } from '@testing-library/react'
import type { ImageArtifact as ImageSpec } from '../../types'
import { ImageArtifact } from './ImageArtifact'

const image = (src: unknown, title = 'Residual map'): ImageSpec => ({ id: 'i', type: 'image', title, src: src as string })

describe('ImageArtifact', () => {
  it('renders the image with the title as alt text', () => {
    render(<ImageArtifact artifact={image('https://example.com/map.png')} />)
    const img = screen.getByRole('img')
    expect(img).toHaveAttribute('src', 'https://example.com/map.png')
    expect(img).toHaveAttribute('alt', 'Residual map')
    expect(img).toHaveAttribute('loading', 'lazy')
  })

  it('holds a fill placeholder until loaded', () => {
    render(<ImageArtifact artifact={image('https://example.com/map.png')} />)
    const img = screen.getByRole('img')
    expect(img.parentElement).toHaveClass('bg-fill')
    fireEvent.load(img)
    expect(img).toHaveClass('opacity-100')
    expect(img.parentElement).not.toHaveClass('bg-fill')
  })

  it('collapses to a muted tile when the image fails', () => {
    render(<ImageArtifact artifact={image('https://example.com/map.png')} />)
    fireEvent.error(screen.getByRole('img'))
    expect(screen.getByText('Image unavailable')).toBeInTheDocument()
  })

  it.each([[''], [undefined], ['data:text/html,<script>1</script>']])('treats the src %j as unavailable', (src) => {
    render(<ImageArtifact artifact={image(src)} />)
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
    expect(screen.getByText('Image unavailable')).toBeInTheDocument()
  })

  it('tries again when the src changes after a failure', () => {
    const { rerender } = render(<ImageArtifact artifact={image('https://example.com/old.png')} />)
    fireEvent.error(screen.getByRole('img'))
    rerender(<ImageArtifact artifact={image('https://example.com/new.png')} />)
    expect(screen.getByRole('img')).toHaveAttribute('src', 'https://example.com/new.png')
  })
})
