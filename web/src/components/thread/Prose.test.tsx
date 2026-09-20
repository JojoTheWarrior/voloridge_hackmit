import { render, screen } from '@testing-library/react'
import { Prose } from './Prose'

describe('Prose', () => {
  it('splits paragraphs on blank lines and keeps single line breaks', () => {
    const { container } = render(<Prose text={'First.\n\nSecond line one\nline two.\n\n\n'} />)
    const paragraphs = container.querySelectorAll('p')
    expect(paragraphs).toHaveLength(2)
    expect(paragraphs[1]).toHaveTextContent('Second line one line two.')
  })

  it('renders the emphasis an assistant tends to write instead of showing the asterisks', () => {
    const { container } = render(<Prose text={'Hotter days go with *cheaper* gas, a **strong** sign; see `dlog(spot)`.'} />)
    expect(screen.getByText('cheaper').tagName).toBe('EM')
    expect(screen.getByText('strong').tagName).toBe('STRONG')
    expect(screen.getByText('dlog(spot)').tagName).toBe('CODE')
    expect(container).not.toHaveTextContent('*')
    expect(container).not.toHaveTextContent('`')
    expect(container).toHaveTextContent('Hotter days go with cheaper gas, a strong sign; see dlog(spot).')
  })

  it.each([
    'Compare 5 * 3 * 2 by hand.',
    'A lone * star and an unclosed *one.',
    'Pointers like **this never close.',
    'Empty pairs ** and `` stay put.',
  ])('leaves %j exactly as written', (text) => {
    const { container } = render(<Prose text={text} />)
    expect(container.querySelector('p')).toHaveTextContent(text, { normalizeWhitespace: false })
    expect(container.querySelector('em, strong, code')).toBeNull()
  })

  it('never turns text into markup', () => {
    const { container } = render(<Prose text={'<img src=x onerror=alert(1)> *<b>bold</b>*'} />)
    expect(container.querySelector('img, b')).toBeNull()
    expect(screen.getByText('<b>bold</b>').tagName).toBe('EM')
  })

  it('renders nothing for blank text', () => {
    const { container } = render(<Prose text={'  \n\n  '} />)
    expect(container.querySelectorAll('p')).toHaveLength(0)
  })
})
