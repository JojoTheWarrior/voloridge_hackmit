import type { ImagesArtifact as ImagesSpec } from '../../types'
import { ArtifactImage } from './ArtifactImage'
import { EmptyBody } from './EmptyBody'
import { asText } from './text'

const COLUMNS: Record<number, string> = { 1: 'sm:grid-cols-2', 2: 'sm:grid-cols-2', 3: 'sm:grid-cols-3' }

export function ImagesArtifact({ artifact }: { artifact: ImagesSpec }) {
  const items = (Array.isArray(artifact.items) ? artifact.items : []).filter((item) => item !== null && typeof item === 'object')
  if (items.length === 0) return <EmptyBody />

  return (
    <div className={`grid grid-cols-2 gap-x-3 gap-y-4 ${COLUMNS[items.length] ?? 'sm:grid-cols-4'}`}>
      {items.map((item, index) => {
        const caption = asText(item.caption)
        return (
          <figure key={index} className="min-w-0">
            <ArtifactImage
              src={item.src}
              alt={caption || `Image ${index + 1}`}
              frameClassName="aspect-[4/3] w-full"
              imageClassName="h-full w-full object-cover"
            />
            {caption && (
              <figcaption className="mt-1.5 truncate text-[11px] text-muted" title={caption}>
                {caption}
              </figcaption>
            )}
          </figure>
        )
      })}
    </div>
  )
}
