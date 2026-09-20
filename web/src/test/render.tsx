import { render } from '@testing-library/react'
import type { ReactElement } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ApiProvider } from '../api/ApiProvider'
import type { Api } from '../api/index'
import { createMockApi } from '../api/mock'
import { MissionLayout } from '../pages/MissionLayout'

interface Options {
  api?: Api
  route?: string
}

export function renderWithApp(ui: ReactElement, { api = createMockApi(), route = '/' }: Options = {}) {
  return {
    api,
    ...render(
      <ApiProvider api={api}>
        <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
      </ApiProvider>,
    ),
  }
}

/** Renders one view of a mission the way the app mounts it: inside the layout that loads the mission and draws the header. */
export function renderMissionView(view: ReactElement, path: '' | 'report' | 'explorer', options: Options & { route: string }) {
  return renderWithApp(
    <Routes>
      <Route path="missions/:id" element={<MissionLayout />}>
        <Route index={path === ''} path={path || undefined} element={view} />
      </Route>
      <Route path="/" element={<p>home page</p>} />
    </Routes>,
    options,
  )
}
