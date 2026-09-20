import { useLayoutEffect, useRef } from 'react'

const NEAR_BOTTOM_PX = 80

/** Keeps a scroll container at its bottom as `length` grows, unless the reader has scrolled up to read. */
export function useStickToBottom<T extends HTMLElement>(length: number) {
  const ref = useRef<T>(null)
  const stuck = useRef(true)

  useLayoutEffect(() => {
    const el = ref.current
    if (el && stuck.current) el.scrollTop = el.scrollHeight
  }, [length])

  return {
    ref,
    onScroll() {
      const el = ref.current
      if (el) stuck.current = el.scrollHeight - el.scrollTop - el.clientHeight <= NEAR_BOTTOM_PX
    },
    /** Follow the next growth whatever the scroll position, e.g. for the reader's own message. */
    stick() {
      stuck.current = true
    },
  }
}
