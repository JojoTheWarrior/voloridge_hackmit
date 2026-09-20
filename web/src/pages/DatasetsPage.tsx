import { useState } from 'react'
import { DatasetCards } from '../components/DatasetCards'
import { DatasetTable } from '../components/DatasetTable'
import { LinkDatasetDialog } from '../components/LinkDatasetDialog'
import { ViewToggle } from '../components/ViewToggle'
import { useDatasets } from '../hooks/useApiData'
import { useDatasetView } from '../hooks/useDatasetView'

const pillClass = 'rounded-full bg-ink px-4 py-1.5 text-[13px] text-paper transition-colors duration-150 hover:bg-ink/85'

export function DatasetsPage() {
  const datasets = useDatasets()
  const [linking, setLinking] = useState(false)
  const [view, setView] = useDatasetView()

  if (!datasets) return null
  const linkButton = (
    <button type="button" onClick={() => setLinking(true)} className={pillClass}>
      Link dataset
    </button>
  )

  return (
    <div className="mx-auto w-full max-w-[880px] px-6 pt-12 pb-24">
      {datasets.length === 0 ? (
        <div className="flex flex-col items-center gap-2 pt-32 text-center">
          <h1 className="text-lg font-medium tracking-tight">Link your first dataset</h1>
          <p className="max-w-xs pb-3 text-sm text-muted">Missions look for connections between the sources you link here.</p>
          {linkButton}
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between gap-4">
            <h1 className="text-2xl font-medium tracking-[-0.025em]">Datasets</h1>
            <div className="flex items-center gap-3">
              <ViewToggle view={view} onChange={setView} />
              {linkButton}
            </div>
          </div>
          <p className="mt-1 mb-9 text-sm text-muted">Sources your missions can draw on.</p>
          {view === 'card' ? <DatasetCards datasets={datasets} /> : <DatasetTable datasets={datasets} />}
        </>
      )}
      {linking && <LinkDatasetDialog onClose={() => setLinking(false)} />}
    </div>
  )
}
