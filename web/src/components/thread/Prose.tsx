import type { ReactNode } from 'react'

// Devin is told to write plain text, but assistants reach for emphasis anyway. Openers and closers must
// hug their text, so "5 * 3 * 2" and a stray asterisk are left alone.
const INLINE = /(\*\*(?=\S)[^*\n]*?\S\*\*|\*(?=\S)[^*\n]*?\S\*|`[^`\n]+`)/

function inline(text: string): ReactNode[] {
  return text.split(INLINE).map((part, i) => {
    if (i % 2 === 0) return part
    if (part.startsWith('**')) {
      return (
        <strong key={i} className="font-medium">
          {part.slice(2, -2)}
        </strong>
      )
    }
    if (part.startsWith('*')) return <em key={i}>{part.slice(1, -1)}</em>
    return (
      <code key={i} className="font-mono text-[13px]">
        {part.slice(1, -1)}
      </code>
    )
  })
}

/** Text as paragraphs, split on blank lines, with light inline emphasis. */
export function Prose({ text, className = '' }: { text: string; className?: string }) {
  const paragraphs = text.split(/\n{2,}/).filter((paragraph) => paragraph.trim() !== '')
  return (
    <div className={`flex flex-col gap-3 text-[15px] leading-[1.65] ${className}`}>
      {paragraphs.map((paragraph, i) => (
        <p key={i} className="whitespace-pre-line">
          {inline(paragraph)}
        </p>
      ))}
    </div>
  )
}
