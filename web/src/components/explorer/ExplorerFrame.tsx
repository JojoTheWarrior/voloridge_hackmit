import { LoaderCircle } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useTheme } from '../../hooks/useTheme'
import type { Explorer } from '../../types'
import { themedSrc } from './src'

const SLOW_MS = 20_000
const INLINE_LINK = 'text-ink underline decoration-line underline-offset-4 transition-colors duration-150 hover:decoration-ink'

interface ExplorerFrameProps {
  explorer: Explorer
  onRequestChange: () => void
}

function Frame({ explorer, onRequestChange }: ExplorerFrameProps) {
  const { theme } = useTheme()
  // The address keeps the theme it started with: changing it would reload the frame and lose the reader's place.
  const [src] = useState(() => themedSrc(explorer, theme))
  const [loaded, setLoaded] = useState(false)
  const [slow, setSlow] = useState(false)
  const frame = useRef<HTMLIFrameElement>(null)

  useEffect(() => {
    if (loaded) return
    const timer = setTimeout(() => setSlow(true), SLOW_MS)
    return () => clearTimeout(timer)
  }, [loaded])

  // The frame's origin is opaque, so there is no narrower target than "*"; the message carries nothing private.
  useEffect(() => {
    if (loaded) frame.current?.contentWindow?.postMessage({ type: 'kingdom:theme', theme }, '*')
  }, [loaded, theme])

  return (
    <div className="relative min-h-0 flex-1 border-t border-line-soft">
      <iframe
        ref={frame}
        title={explorer.title}
        src={src}
        sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox"
        referrerPolicy="no-referrer"
        loading="eager"
        allow="fullscreen"
        onLoad={() => setLoaded(true)}
        className="block h-full w-full"
      />
      {!loaded && (
        <div role="status" className="fade-in absolute inset-0 flex flex-col items-center justify-center gap-3 bg-paper px-6 pb-16 text-center text-sm text-muted">
          <LoaderCircle size={16} strokeWidth={1.75} aria-hidden="true" className="animate-spin" />
          {slow ? (
            <p className="max-w-sm leading-relaxed">
              This is taking longer than usual.{' '}
              <a href={themedSrc(explorer, theme)} target="_blank" rel="noreferrer" aria-label="Open in new tab" className={INLINE_LINK}>
                Open it in a new tab
              </a>
              , or{' '}
              <button type="button" onClick={onRequestChange} className={INLINE_LINK}>
                request a change
              </button>{' '}
              if it never appears.
            </p>
          ) : (
            <p>Loading the explorer</p>
          )}
        </div>
      )}
    </div>
  )
}

/** The explorer in its sandbox. A new build gets a new frame, so it starts loading from scratch. */
export function ExplorerFrame({ explorer, onRequestChange }: ExplorerFrameProps) {
  return <Frame key={explorer.version} explorer={explorer} onRequestChange={onRequestChange} />
}
