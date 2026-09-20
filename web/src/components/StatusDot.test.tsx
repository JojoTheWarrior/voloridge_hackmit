import { render, screen } from '@testing-library/react'
import { StatusDot } from './StatusDot'

describe('StatusDot', () => {
  it.each([
    ['running', 'Running'],
    ['done', 'Done'],
    ['failed', 'Failed'],
  ] as const)('labels %s as %s', (status, label) => {
    render(<StatusDot status={status} />)
    expect(screen.getByRole('img', { name: label })).toBeInTheDocument()
  })
})
