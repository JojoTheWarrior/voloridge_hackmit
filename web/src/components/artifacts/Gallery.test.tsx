import { render, screen } from '@testing-library/react'
import { ArtifactGallery } from './Gallery'
import { galleryArtifacts } from './galleryFixtures'

describe('ArtifactGallery', () => {
  it('shows an example of every artifact type', () => {
    expect(new Set(galleryArtifacts.map((artifact) => artifact.type))).toEqual(new Set(['chart', 'images', 'relation', 'table', 'stats', 'image']))
  })

  it('renders every example as a figure', () => {
    render(<ArtifactGallery />)
    for (const artifact of galleryArtifacts) expect(screen.getByRole('figure', { name: artifact.title })).toBeInTheDocument()
  })
})
