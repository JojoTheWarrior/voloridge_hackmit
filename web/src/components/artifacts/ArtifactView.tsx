import type { ReactNode } from 'react'
import type { Artifact } from '../../types'
import { ChartArtifact } from './ChartArtifact'
import { ImageArtifact } from './ImageArtifact'
import { ImagesArtifact } from './ImagesArtifact'
import { RelationArtifact } from './RelationArtifact'
import { StatsArtifact } from './StatsArtifact'
import { TableArtifact } from './TableArtifact'
import { asText } from './text'

function body(artifact: Artifact): ReactNode {
  switch (artifact?.type) {
    case 'chart':
      return <ChartArtifact artifact={artifact} />
    case 'images':
      return <ImagesArtifact artifact={artifact} />
    case 'relation':
      return <RelationArtifact artifact={artifact} />
    case 'table':
      return <TableArtifact artifact={artifact} />
    case 'stats':
      return <StatsArtifact artifact={artifact} />
    case 'image':
      return <ImageArtifact artifact={artifact} />
    default:
      return null
  }
}

/** Renders one artifact in the mission thread. Unknown types render nothing. */
export function ArtifactView({ artifact }: { artifact: Artifact }) {
  const content = body(artifact)
  if (!content) return null

  const title = asText(artifact.title) || 'Untitled'
  const headline = artifact.type === 'chart' ? asText(artifact.headline) : ''
  const caption = asText(artifact.caption)

  return (
    <figure aria-label={title} className="fade-in min-w-0 rounded-xl border border-line p-5">
      <div className="flex items-baseline justify-between gap-4 pb-4">
        <h3 className="line-clamp-2 min-w-0 text-[13px] font-medium break-words" title={title}>
          {title}
        </h3>
        {headline && (
          <span className="max-w-[50%] shrink-0 truncate font-mono text-[13px]" title={headline}>
            {headline}
          </span>
        )}
      </div>
      {content}
      {caption && <figcaption className="pt-4 text-xs leading-relaxed text-muted">{caption}</figcaption>}
    </figure>
  )
}
