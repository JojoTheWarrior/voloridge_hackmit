import { render, screen } from '@testing-library/react'
import { CastleLogo } from './CastleLogo'

describe('CastleLogo', () => {
  it('renders an svg named kingdom', () => {
    render(<CastleLogo />)
    expect(screen.getByRole('img', { name: 'kingdom' })).toBeInTheDocument()
  })

  it('defaults to 16px and honours size', () => {
    const { rerender } = render(<CastleLogo />)
    expect(screen.getByRole('img')).toHaveAttribute('width', '16')
    rerender(<CastleLogo size={28} />)
    expect(screen.getByRole('img')).toHaveAttribute('width', '28')
    expect(screen.getByRole('img')).toHaveAttribute('height', '28')
  })
})
