import { ArrowUp, LoaderCircle } from 'lucide-react'
import { useRef, useState, type KeyboardEvent } from 'react'

export function ReplyComposer({ onSend, initialValue = '', working = false }: { onSend: (text: string) => Promise<void>; initialValue?: string; working?: boolean }) {
  const [value, setValue] = useState(initialValue)
  const [sending, setSending] = useState(false)
  const [failed, setFailed] = useState(false)
  // State lags a render behind; the ref is what stops a second Enter in the same tick.
  const locked = useRef(false)
  const idle = value.trim() === '' || sending

  async function send() {
    const text = value.trim()
    if (!text || locked.current) return
    locked.current = true
    setSending(true)
    setFailed(false)
    try {
      await onSend(text)
      setValue('')
    } catch {
      setFailed(true)
    } finally {
      locked.current = false
      setSending(false)
    }
  }

  function onKeyDown(event: KeyboardEvent) {
    if (event.key !== 'Enter' || event.shiftKey || event.nativeEvent.isComposing) return
    event.preventDefault()
    send()
  }

  return (
    <div>
      <div className="flex items-end gap-3 rounded-2xl border border-line bg-paper p-2 pl-3 transition-colors duration-150 focus-within:border-ink">
        <textarea
          aria-label="Reply to Devin"
          autoFocus={Boolean(initialValue)}
          readOnly={sending}
          rows={1}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder={working ? 'Steer the research…' : 'Ask a follow-up or take this further…'}
          className="field-sizing-content block max-h-48 min-h-8 w-full resize-none bg-transparent px-1 py-1 text-[15px] leading-relaxed outline-none placeholder:text-muted"
        />
        <button
          type="button"
          aria-label="Send reply"
          aria-disabled={idle}
          aria-busy={sending}
          onClick={send}
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-paper transition-colors duration-150 ${
            idle ? 'cursor-default bg-line' : 'bg-ink hover:bg-ink/85'
          }`}
        >
          {sending ? <LoaderCircle size={16} strokeWidth={2} aria-hidden="true" className="animate-spin" /> : <ArrowUp size={16} strokeWidth={2} aria-hidden="true" />}
        </button>
      </div>
      {working && <p className="px-3 pt-2 text-[11px] leading-relaxed text-muted">Runs on its own. Send a message anytime to guide it.</p>}
      {failed && (
        <p role="status" className="px-3 pt-2 text-[13px] text-muted">
          That did not send. Try again.
        </p>
      )}
    </div>
  )
}
