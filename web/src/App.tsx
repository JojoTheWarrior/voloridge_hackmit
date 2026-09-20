import { Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { DatasetsPage } from './pages/DatasetsPage'
import { MissionPage } from './pages/MissionPage'
import { NewMissionPage } from './pages/NewMissionPage'

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<NewMissionPage />} />
        <Route path="missions/:id" element={<MissionPage />} />
        <Route path="datasets" element={<DatasetsPage />} />
      </Route>
    </Routes>
  )
}
