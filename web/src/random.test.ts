import { hash, mulberry32 } from './random'

describe('hash', () => {
  it('is a stable unsigned 32-bit integer', () => {
    expect(hash('')).toBe(2166136261)
    expect(hash('gdelt')).toBe(hash('gdelt'))
    expect(Number.isInteger(hash('gdelt'))).toBe(true)
    expect(hash('a long id with spaces and ünicode')).toBeGreaterThanOrEqual(0)
  })

  it('separates nearby strings', () => {
    expect(hash('d-1')).not.toBe(hash('d-2'))
  })
})

describe('mulberry32', () => {
  const take = (seed: number, count = 50) => {
    const rand = mulberry32(seed)
    return Array.from({ length: count }, rand)
  }

  it('repeats the same sequence for the same seed', () => {
    expect(take(7)).toEqual(take(7))
  })

  it('gives different sequences for different seeds', () => {
    expect(take(7)).not.toEqual(take(8))
  })

  it('stays within [0, 1)', () => {
    for (const seed of [0, 1, 0xffffffff]) take(seed, 500).forEach((v) => expect(v >= 0 && v < 1).toBe(true))
  })
})
