/** Plain text as paragraphs, split on blank lines. */
export function Prose({ text, className = '' }: { text: string; className?: string }) {
  const paragraphs = text.split(/\n{2,}/).filter((paragraph) => paragraph.trim() !== '')
  return (
    <div className={`flex flex-col gap-3 text-[15px] leading-[1.65] ${className}`}>
      {paragraphs.map((paragraph, i) => (
        <p key={i} className="whitespace-pre-line">
          {paragraph}
        </p>
      ))}
    </div>
  )
}
