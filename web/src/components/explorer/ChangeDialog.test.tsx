import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ValidationError } from '../../api/index'
import { ChangeDialog } from './ChangeDialog'

function renderDialog(onSubmit = vi.fn<(instructions: string) => Promise<void>>(async () => {})) {
  const onClose = vi.fn()
  const view = render(<ChangeDialog onSubmit={onSubmit} onClose={onClose} />)
  return { ...view, onSubmit, onClose, user: userEvent.setup() }
}

const box = () => screen.getByRole('textbox', { name: 'What should change?' })
const send = () => screen.getByRole('button', { name: 'Send to Devin' })

describe('ChangeDialog', () => {
  it('opens as a modal with one question, a ghost cancel and the one filled button', () => {
    const { container } = renderDialog()
    expect(screen.getByRole('dialog', { name: 'Request a change' })).toHaveAttribute('open')
    expect(box()).toHaveAttribute('placeholder', 'Add a heatmap layer')
    expect(box()).toHaveFocus()
    expect(screen.getByRole('button', { name: 'Cancel' })).toHaveClass('text-muted')
    expect(container.querySelectorAll('[class*="bg-ink"]')).toHaveLength(1)
    expect(send()).toHaveClass('bg-ink', 'text-paper')
  })

  it('sends what was typed, trimmed, then closes', async () => {
    const { onSubmit, onClose, user } = renderDialog()
    await user.type(box(), '  Add a heatmap layer ')
    await user.click(send())
    expect(onSubmit).toHaveBeenCalledExactlyOnceWith('Add a heatmap layer')
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('sends nothing at all as a plain rebuild', async () => {
    const { onSubmit, onClose, user } = renderDialog()
    await user.click(send())
    expect(onSubmit).toHaveBeenCalledExactlyOnceWith('')
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it.each(['{Meta>}{Enter}{/Meta}', '{Control>}{Enter}{/Control}'])('submits on %s', async (keys) => {
    const { onSubmit, user } = renderDialog()
    await user.type(box(), `Color by score${keys}`)
    expect(onSubmit).toHaveBeenCalledExactlyOnceWith('Color by score')
  })

  it('keeps a plain Enter as a new line', async () => {
    const { onSubmit, user } = renderDialog()
    await user.type(box(), 'One{Enter}Two')
    expect(onSubmit).not.toHaveBeenCalled()
    expect(box()).toHaveValue('One\nTwo')
  })

  it('closes on cancel without sending', async () => {
    const { onSubmit, onClose, user } = renderDialog()
    await user.type(box(), 'Never mind')
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(onSubmit).not.toHaveBeenCalled()
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  describe('the 2,000 character limit', () => {
    const type = (length: number) => fireEvent.change(box(), { target: { value: 'x'.repeat(length) } })

    it('says nothing about it until the text gets close', () => {
      renderDialog()
      type(1799)
      expect(screen.queryByText(/\/ 2,000/)).not.toBeInTheDocument()
      type(1800)
      expect(screen.getByText('1,800 / 2,000')).toHaveClass('font-mono', 'text-muted')
    })

    it('still sends at exactly the limit', async () => {
      const { onSubmit, user } = renderDialog()
      type(2000)
      await user.click(send())
      expect(onSubmit).toHaveBeenCalledTimes(1)
    })

    it('holds the text back once it is over, by button and by shortcut', async () => {
      const { onSubmit, onClose, user } = renderDialog()
      type(2001)
      expect(screen.getByText('2,001 / 2,000')).toHaveClass('text-ink')
      expect(send()).toHaveAttribute('aria-disabled', 'true')
      await user.click(send())
      await user.type(box(), '{Meta>}{Enter}{/Meta}')
      expect(onSubmit).not.toHaveBeenCalled()
      expect(onClose).not.toHaveBeenCalled()
    })

    it('counts what will be sent, not the space around it', () => {
      renderDialog()
      fireEvent.change(box(), { target: { value: `  ${'x'.repeat(2000)}\n` } })
      expect(screen.getByText('2,000 / 2,000')).toHaveClass('text-muted')
      expect(send()).not.toHaveAttribute('aria-disabled', 'true')
    })
  })

  it('shows what the server objected to, stays open, and clears it on the next edit', async () => {
    const onSubmit = vi.fn().mockRejectedValueOnce(new ValidationError('text', 'Keep instructions under 2,000 characters'))
    const { onClose, user } = renderDialog(onSubmit)
    await user.type(box(), 'Too much')
    await user.click(send())
    expect(await screen.findByText('Keep instructions under 2,000 characters')).toBeInTheDocument()
    expect(box()).toHaveAttribute('aria-invalid', 'true')
    expect(box()).toHaveAccessibleDescription('Keep instructions under 2,000 characters')
    expect(onClose).not.toHaveBeenCalled()

    await user.type(box(), '!')
    expect(screen.queryByText('Keep instructions under 2,000 characters')).not.toBeInTheDocument()
    expect(box()).toHaveAttribute('aria-invalid', 'false')
  })

  it('says so quietly when the request does not get through, and lets you try again', async () => {
    const onSubmit = vi.fn().mockRejectedValueOnce(new TypeError('Failed to fetch')).mockResolvedValueOnce(undefined)
    const { onClose, user } = renderDialog(onSubmit)
    await user.type(box(), 'Add a legend')
    await user.click(send())
    expect(await screen.findByText('That did not send. Try again.')).toBeInTheDocument()
    expect(box()).toHaveValue('Add a legend')
    expect(onClose).not.toHaveBeenCalled()

    await user.click(send())
    expect(onSubmit).toHaveBeenCalledTimes(2)
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('sends once however fast it is pressed', async () => {
    let finish = () => {}
    const onSubmit = vi.fn(() => new Promise<void>((resolve) => (finish = resolve)))
    const { user } = renderDialog(onSubmit)
    await user.dblClick(send())
    await user.type(box(), '{Meta>}{Enter}{/Meta}')
    expect(onSubmit).toHaveBeenCalledTimes(1)
    expect(send()).toHaveAttribute('aria-disabled', 'true')
    await act(async () => finish())
  })
})
