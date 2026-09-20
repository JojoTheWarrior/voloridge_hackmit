export function ErrorEvent({ text }: { text: string }) {
  return (
    <div role="alert" className="fade-in rounded-xl border border-line p-5 text-[15px] leading-relaxed">
      {text}
    </div>
  )
}
