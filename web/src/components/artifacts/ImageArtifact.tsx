import type { ImageArtifact as ImageSpec } from '../../types'
import { ArtifactImage } from './ArtifactImage'
import { asText } from './text'

export function ImageArtifact({ artifact }: { artifact: ImageSpec }) {
  return (
    <ArtifactImage
      src={artifact.src}
      alt={asText(artifact.title) || 'Image'}
      frameClassName="flex min-h-[120px] w-full items-center justify-center"
      imageClassName="max-h-[440px] max-w-full object-contain"
    />
  )
}
