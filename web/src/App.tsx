import { Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { DatasetsPage } from './pages/DatasetsPage'
import { ExplorerPage } from './pages/ExplorerPage'
import { MissionLayout } from './pages/MissionLayout'
import { MissionPage } from './pages/MissionPage'
import { NewMissionPage } from './pages/NewMissionPage'
import { ReportPage } from './pages/ReportPage'

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<NewMissionPage />} />
        <Route path="missions/:id" element={<MissionLayout />}>
          <Route index element={<MissionPage />} />
          <Route path="report" element={<ReportPage />} />
          <Route path="explorer" element={<ExplorerPage />} />
        </Route>
        <Route path="datasets" element={<DatasetsPage />} />
      </Route>
    </Routes>
  )
}
