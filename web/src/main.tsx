import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ApiProvider } from './api/ApiProvider'
import { createHttpApi } from './api/http'
import { App } from './App'
import './index.css'

const api = createHttpApi()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ApiProvider api={api}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ApiProvider>
  </StrictMode>,
)
