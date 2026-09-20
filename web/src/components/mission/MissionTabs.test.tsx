import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { makeExplorer, makeMission, makeReport } from '../../test/missions'
import type { Mission } from '../../types'
import { MissionTabs } from './MissionTabs'

function renderTabs(mission: Mission, route = `/missions/${encodeURIComponent(mission.id)}`) {
  render(
    <MemoryRouter initialEntries={[route]}>
      <MissionTabs mission={mission} />
    </MemoryRouter>,
  )
  return within(screen.getByRole('navigation', { name: 'Mission views' }))
}

describe('MissionTabs', () => {
  it('links to the three views of the mission, escaping its id', () => {
    const tabs = renderTabs(makeMission('waiting', { id: 'm 1' }))
    expect(tabs.getAllByRole('link').map((link) => [link.textContent, link.getAttribute('href')])).toEqual([
      ['Thread', '/missions/m%201'],
      ['Report', '/missions/m%201/report'],
      ['Explorer', '/missions/m%201/explorer'],
    ])
  })

  it.each([
    ['', 'Thread'],
    ['/report', 'Report'],
    ['/explorer', 'Explorer'],
  ])('marks the view at "%s" as the current page, and only that one', (suffix, current) => {
    const mission = makeMission('waiting', { id: 'm1' })
    const tabs = renderTabs(mission, `/missions/m1${suffix}`)
    for (const link of tabs.getAllByRole('link')) {
      if (link.textContent === current) {
        expect(link).toHaveAttribute('aria-current', 'page')
        expect(link).toHaveClass('bg-fill', 'text-ink')
      } else {
        expect(link).not.toHaveAttribute('aria-current')
        expect(link).toHaveClass('text-muted')
        expect(link).not.toHaveClass('bg-fill')
      }
    }
  })

  it('is a quiet segmented control: round, small, no filled ink', () => {
    const tabs = renderTabs(makeMission('waiting'))
    tabs.getAllByRole('link').forEach((link) => expect(link).toHaveClass('rounded-full', 'text-[13px]'))
    expect(screen.getByRole('navigation').querySelector('[class*="bg-ink"]')).toBeNull()
  })

  it('carries no marker while there is nothing to see', () => {
    const tabs = renderTabs(makeMission('waiting'))
    expect(tabs.getByRole('link', { name: 'Report' })).toBeInTheDocument()
    expect(tabs.getByRole('link', { name: 'Explorer' })).toBeInTheDocument()
    expect(screen.getByRole('navigation').querySelector('svg, [data-marker]')).toBeNull()
  })

  it('dots a view whose content is ready, and says so to a screen reader', () => {
    const tabs = renderTabs(makeMission('done', { report: makeReport(), explorer: makeExplorer() }))
    for (const name of ['Report, ready', 'Explorer, ready']) {
      expect(tabs.getByRole('link', { name }).querySelector('[data-marker="ready"]')).not.toBeNull()
    }
    expect(tabs.getByRole('link', { name: 'Thread' }).querySelector('[data-marker]')).toBeNull()
  })

  it('spins on a view Devin is working on, even when an earlier version is ready', () => {
    const tabs = renderTabs(makeMission('working', { reportPending: true, explorer: makeExplorer(), explorerPending: true }))
    for (const name of ['Report, in progress', 'Explorer, in progress']) {
      const link = tabs.getByRole('link', { name })
      expect(link.querySelector('svg')).toHaveClass('animate-spin')
      expect(link.querySelector('[data-marker="ready"]')).toBeNull()
    }
  })
})
