import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { MissionEvent } from '../../types'
import { WorkLog } from './WorkLog'

const events: MissionEvent[] = [
  { id: 'e1', at: '2026-09-20T12:00:00Z', kind: 'step', stepId: 's1', label: 'Read both datasets', state: 'done' },
  { id: 'e2', at: '2026-09-20T12:01:00Z', kind: 'thought', text: 'Both cover the same window.' },
]

describe('WorkLog', () => {
  it('starts folded and opens and closes on click', async () => {
    const user = userEvent.setup()
    render(<WorkLog events={events} />)
    const toggle = screen.getByRole('button', { name: 'Show the work' })
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByText('Read both datasets')).not.toBeInTheDocument()

    await user.click(toggle)
    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('Read both datasets')).toBeInTheDocument()
    expect(screen.getByText('Both cover the same window.')).toBeInTheDocument()

    await user.click(toggle)
    expect(screen.queryByText('Read both datasets')).not.toBeInTheDocument()
  })

  it('renders nothing when there is no work to show', () => {
    const { container } = render(<WorkLog events={[]} />)
    expect(container).toBeEmptyDOMElement()
  })
})
