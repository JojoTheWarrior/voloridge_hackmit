import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ApiProvider } from './api/context'
import { createMockApi } from './api/mock'
import { App } from './App'
import './index.css'

const api = createMockApi()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ApiProvider api={api}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ApiProvider>
  </StrictMode>,
)
