import { useState } from 'react'

// Anything else (javascript:, data:, an unresolved attachment: ref) is never requested.
const USABLE_SRC = /^(https?:\/\/|\/)/i

const isUsable = (src: unknown): src is string => typeof src === 'string' && USABLE_SRC.test(src)

interface ArtifactImageProps {
  src: unknown
  alt: string
  /** Sizing for the frame that holds the placeholder, the image, or the unavailable tile. */
  frameClassName: string
  imageClassName: string
}

function LoadedImage({ src, alt, frameClassName, imageClassName }: ArtifactImageProps & { src: string }) {
  const [state, setState] = useState<'loading' | 'loaded' | 'failed'>('loading')
  if (state === 'failed') return <Unavailable className={frameClassName} />
  return (
    <div className={`overflow-hidden rounded-md ${state === 'loading' ? 'bg-fill' : ''} ${frameClassName}`}>
      <img
        src={src}
        alt={alt}
        loading="lazy"
        onLoad={() => setState('loaded')}
        onError={() => setState('failed')}
        className={`transition-opacity duration-150 ${state === 'loaded' ? 'opacity-100' : 'opacity-0'} ${imageClassName}`}
      />
    </div>
  )
}

function Unavailable({ className }: { className: string }) {
  return <div className={`flex items-center justify-center rounded-md bg-fill px-2 text-center text-[11px] text-muted ${className}`}>Image unavailable</div>
}

export function ArtifactImage(props: ArtifactImageProps) {
  if (!isUsable(props.src)) return <Unavailable className={props.frameClassName} />
  // Keyed by src so a new URL starts from the placeholder instead of inheriting a failure.
  return <LoadedImage key={props.src} {...props} src={props.src} />
}
