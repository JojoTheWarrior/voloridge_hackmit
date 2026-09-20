import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'

interface DeliveryCardProps {
  /** Names the card for assistive tech, e.g. "Report". */
  label: string
  eyebrow: string
  title: string
  summary: string
  to: string
  action: string
}

/** Marks where in the thread something Devin built arrived. The link is stretched over the card, so all of it opens the view. */
export function DeliveryCard({ label, eyebrow, title, summary, to, action }: DeliveryCardProps) {
  return (
    <section
      aria-label={label}
      className="fade-in group relative rounded-xl border border-line p-5 transition-colors duration-150 hover:border-faint"
    >
      <p className="text-xs text-muted">{eyebrow}</p>
      <p className="mt-2 text-[17px] leading-snug font-medium tracking-tight text-balance">{title}</p>
      <p className="mt-1.5 line-clamp-2 text-[13px] leading-relaxed text-muted">{summary}</p>
      <Link to={to} className="mt-4 inline-flex items-center gap-1 text-[13px] font-medium after:absolute after:inset-0 after:rounded-xl">
        {action}
        <ArrowRight size={14} strokeWidth={1.75} aria-hidden="true" className="transition-transform duration-150 group-hover:translate-x-0.5" />
      </Link>
    </section>
  )
}
