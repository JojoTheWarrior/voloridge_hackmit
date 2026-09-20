import { render } from '@testing-library/react'
import type { ReactElement } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { ApiProvider } from '../api/ApiProvider'
import type { Api } from '../api/index'
import { createMockApi } from '../api/mock'

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
