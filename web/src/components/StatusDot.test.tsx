import { render, screen } from '@testing-library/react'
import { StatusDot } from './StatusDot'

describe('StatusDot', () => {
  it.each([
    ['working', 'Working'],
    ['waiting', 'Waiting for you'],
    ['done', 'Done'],
    ['failed', 'Failed'],
  ] as const)('labels %s as %s', (status, label) => {
    render(<StatusDot status={status} />)
    expect(screen.getByRole('img', { name: label })).toBeInTheDocument()
  })

  it('fills and pulses the working dot', () => {
    render(<StatusDot status="working" />)
    const circle = screen.getByRole('img').querySelector('circle')
    expect(circle).toHaveAttribute('fill', 'currentColor')
    expect(circle).toHaveClass('animate-pulse')
    expect(screen.getByRole('img').querySelector('path')).toBeNull()
  })

  it.each(['waiting', 'done', 'failed'] as const)('draws %s as a still, hollow ring', (status) => {
    render(<StatusDot status={status} />)
    const circle = screen.getByRole('img').querySelector('circle')
    expect(circle).toHaveAttribute('fill', 'none')
    expect(circle).not.toHaveClass('animate-pulse')
  })

  it('tells waiting, done and failed apart by their mark', () => {
    const mark = (status: 'waiting' | 'done' | 'failed') => {
      const { container, unmount } = render(<StatusDot status={status} />)
      const path = container.querySelector('path')
      const summary = path && { filled: path.getAttribute('fill') === 'currentColor', stroked: path.hasAttribute('stroke') }
      unmount()
      return summary
    }
    expect(mark('waiting')).toEqual({ filled: true, stroked: false })
    expect(mark('done')).toBeNull()
    expect(mark('failed')).toEqual({ filled: false, stroked: true })
  })
})
