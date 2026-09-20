import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ReplyComposer } from './ReplyComposer'

function renderComposer(onSend = vi.fn().mockResolvedValue(undefined)) {
  render(<ReplyComposer onSend={onSend} />)
  return { onSend, user: userEvent.setup() }
}

const input = () => screen.getByRole('textbox', { name: 'Reply to Devin' })
const button = () => screen.getByRole('button', { name: 'Send reply' })

describe('ReplyComposer', () => {
  it('invites a reply without stealing focus', () => {
    renderComposer()
    expect(input()).toHaveAttribute('placeholder', 'Reply to Devin')
    expect(input()).not.toHaveFocus()
    expect(button()).toHaveAttribute('aria-disabled', 'true')
  })

  it('sends the trimmed text on Enter and clears the box', async () => {
    const { onSend, user } = renderComposer()
    await user.type(input(), '  Drop the outlier.  {Enter}')
    expect(onSend).toHaveBeenCalledExactlyOnceWith('Drop the outlier.')
    expect(input()).toHaveValue('')
  })

  it('sends from the button', async () => {
    const { onSend, user } = renderComposer()
    await user.type(input(), 'Keep it')
    expect(button()).toHaveAttribute('aria-disabled', 'false')
    await user.click(button())
    expect(onSend).toHaveBeenCalledExactlyOnceWith('Keep it')
  })

  it('inserts a newline on Shift+Enter without sending', async () => {
    const { onSend, user } = renderComposer()
    await user.type(input(), 'line one{Shift>}{Enter}{/Shift}line two')
    expect(input()).toHaveValue('line one\nline two')
    expect(onSend).not.toHaveBeenCalled()
  })

  it.each(['{Enter}', '   {Enter}', '{Shift>}{Enter}{/Shift}{Enter}'])('ignores a blank reply (%j)', async (keys) => {
    const { onSend, user } = renderComposer()
    await user.type(input(), keys)
    await user.click(button())
    expect(onSend).not.toHaveBeenCalled()
  })

  it('does not send while an input method is composing', () => {
    const { onSend } = renderComposer()
    fireEvent.change(input(), { target: { value: 'こんにちは' } })
    fireEvent.keyDown(input(), { key: 'Enter', isComposing: true })
    expect(onSend).not.toHaveBeenCalled()
  })

  it('sends once, and looks disabled, while a send is in flight', async () => {
    let finish = () => {}
    const onSend = vi.fn(() => new Promise<void>((resolve) => (finish = resolve)))
    const { user } = renderComposer(onSend)
    await user.type(input(), 'Only once{Enter}{Enter}')
    await user.click(button())
    expect(onSend).toHaveBeenCalledTimes(1)
    expect(button()).toHaveAttribute('aria-disabled', 'true')
    expect(input()).toHaveValue('Only once')

    finish()
    await vi.waitFor(() => expect(input()).toHaveValue(''))

    await user.type(input(), 'And again{Enter}')
    expect(onSend).toHaveBeenCalledTimes(2)
  })

  it('keeps the text and says so when sending fails, then lets you retry', async () => {
    const onSend = vi.fn().mockRejectedValueOnce(new TypeError('Failed to fetch')).mockResolvedValue(undefined)
    const { user } = renderComposer(onSend)
    await user.type(input(), 'Try me{Enter}')
    expect(await screen.findByText('That did not send. Try again.')).toBeInTheDocument()
    expect(input()).toHaveValue('Try me')

    await user.type(input(), '{Enter}')
    expect(onSend).toHaveBeenCalledTimes(2)
    await vi.waitFor(() => expect(input()).toHaveValue(''))
    expect(screen.queryByText('That did not send. Try again.')).not.toBeInTheDocument()
  })
})
