import { Prose } from './Prose'

export function ThoughtEvent({ text }: { text: string }) {
  return <Prose text={text} className="fade-in" />
}
