import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { makeReport } from '../../test/missions'
import type { Artifact, MissionEvent } from '../../types'
import { EventList } from './EventList'

vi.mock('../artifacts/ArtifactView', () => ({
  ArtifactView: ({ artifact }: { artifact: Artifact }) => <div data-testid="artifact">{artifact.title}</div>,
}))

const at = '2026-09-20T12:00:00Z'
const stats: Artifact = { id: 'a1', type: 'stats', title: 'Core stats', items: [] }

const thread: MissionEvent[] = [
  { id: 'e1', at, kind: 'user_message', text: 'Does A lead B?' },
  { id: 'e2', at, kind: 'step', stepId: 's1', label: 'Read both datasets', state: 'done' },
  { id: 'e3', at, kind: 'thought', text: 'The imagery set has 2,140 tiles.\n\nMost are from one county.' },
  { id: 'e4', at, kind: 'artifact', artifact: stats },
  { id: 'e5', at, kind: 'step', stepId: 's2', label: 'Join on county', state: 'active' },
  { id: 'e6', at, kind: 'error', text: 'Lost contact with Devin, still retrying' },
  { id: 'e7', at, kind: 'user_message', text: 'Keep going' },
  { id: 'e8', at, kind: 'conclusion', verdict: 'A real but modest link.', summary: 'First.\n\nSecond.', stats: [{ label: 'Correlation', value: '0.58' }] },
]

describe('EventList', () => {
  it('renders every kind of event, in thread order', () => {
    const { container } = render(<EventList events={thread} live />)
    const text = container.textContent ?? ''
    const order = ['Does A lead B?', 'Read both datasets', 'The imagery set', 'Core stats', 'Join on county', 'Lost contact', 'Keep going', 'A real but modest link.']
    const positions = order.map((snippet) => text.indexOf(snippet))
    expect(positions.every((p) => p >= 0)).toBe(true)
    expect(positions).toEqual([...positions].sort((a, b) => a - b))
  })

  it('shows user messages as right-aligned bubbles and thoughts as plain prose', () => {
    render(<EventList events={thread} live />)
    for (const text of ['Does A lead B?', 'Keep going']) {
      expect(screen.getByText(text)).toHaveClass('bg-fill')
      expect(screen.getByText(text).parentElement).toHaveClass('justify-end')
    }
    const thought = screen.getByText('The imagery set has 2,140 tiles.')
    expect(thought.tagName).toBe('P')
    expect(thought).not.toHaveClass('bg-fill')
    expect(screen.getByText('Most are from one county.').tagName).toBe('P')
  })

  it('hands artifacts to ArtifactView', () => {
    render(<EventList events={thread} live />)
    expect(screen.getByTestId('artifact')).toHaveTextContent('Core stats')
  })

  it('marks the active step as current only while the mission is live', () => {
    const { rerender } = render(<EventList events={thread} live />)
    expect(screen.getByText('Join on county')).toHaveAttribute('aria-current', 'step')
    expect(screen.getByText('Read both datasets')).not.toHaveAttribute('aria-current')
    expect(screen.getByText('Read both datasets')).toHaveClass('text-muted')

    rerender(<EventList events={thread} live={false} />)
    expect(screen.getByText('Join on county')).not.toHaveAttribute('aria-current')
    expect(screen.getByText('Join on county')).toHaveClass('text-muted')
  })

  it('announces errors', () => {
    render(<EventList events={thread} live />)
    expect(screen.getByRole('alert')).toHaveTextContent('Lost contact with Devin, still retrying')
  })

  it('renders the conclusion with verdict, prose and mono stats', () => {
    render(<EventList events={thread} live />)
    const card = within(screen.getByRole('region', { name: 'Conclusion' }))
    expect(card.getByText('A real but modest link.')).toHaveClass('font-medium')
    expect(card.getByText('First.').tagName).toBe('P')
    expect(card.getByText('Second.').tagName).toBe('P')
    expect(card.getByText('Correlation').tagName).toBe('DT')
    expect(card.getByText('0.58')).toHaveClass('font-mono')
  })

  it('leaves out the stat grid when a conclusion has no stats', () => {
    render(<EventList events={[{ id: 'c', at, kind: 'conclusion', verdict: 'Nothing here.', summary: '', stats: [] }]} live={false} />)
    const card = screen.getByRole('region', { name: 'Conclusion' })
    expect(card.querySelector('dl')).toBeNull()
    expect(card.querySelectorAll('p')).toHaveLength(1)
  })

  it('renders nothing for an empty thread', () => {
    const { container } = render(<EventList events={[]} live />)
    expect(container.textContent).toBe('')
  })

  describe('report event', () => {
    const events: MissionEvent[] = [thread[7], { id: 'report', at, kind: 'report' }]
    const longSummary = 'A long summary sentence that goes on. '.repeat(12).trim()

    function renderReported(report?: ReturnType<typeof makeReport>) {
      return render(
        <MemoryRouter>
          <EventList events={events} live={false} missionId="m 1" report={report} />
        </MemoryRouter>,
      )
    }

    it('shows a card with the headline, a clamped summary and a link to the report', () => {
      renderReported(makeReport({ summary: longSummary }))
      const card = within(screen.getByRole('region', { name: 'Report' }))
      expect(card.getByText('Report ready')).toHaveClass('text-muted')
      expect(card.getByText('Wind leads dust by two days')).toHaveClass('font-medium')
      expect(card.getByText(longSummary)).toHaveClass('line-clamp-2', 'text-muted')
      expect(card.getByRole('link', { name: 'View report' })).toHaveAttribute('href', '/missions/m%201/report')
    })

    it('sits after the conclusion', () => {
      renderReported(makeReport())
      const conclusion = screen.getByRole('region', { name: 'Conclusion' })
      const card = screen.getByRole('region', { name: 'Report' })
      expect(conclusion.compareDocumentPosition(card) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    })

    it('renders nothing for the event when the report itself is missing', () => {
      renderReported()
      expect(screen.queryByRole('region', { name: 'Report' })).not.toBeInTheDocument()
      expect(screen.queryByText('Report ready')).not.toBeInTheDocument()
      expect(screen.getByRole('region', { name: 'Conclusion' })).toBeInTheDocument()
    })
  })
})
