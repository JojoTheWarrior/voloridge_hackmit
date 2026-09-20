import { useState } from 'react'

export type DatasetView = 'list' | 'card'

const STORAGE_KEY = 'kingdom.datasets.view'

function readView(): DatasetView {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'card' ? 'card' : 'list'
  } catch {
    return 'list'
  }
}

function writeView(view: DatasetView) {
  try {
    localStorage.setItem(STORAGE_KEY, view)
  } catch {
    // Browsers can block storage (private mode, site data disabled); the choice then lasts for this visit only.
  }
}

export function useDatasetView(): [DatasetView, (view: DatasetView) => void] {
  const [view, setView] = useState(readView)

  const choose = (next: DatasetView) => {
    setView(next)
    writeView(next)
  }

  return [view, choose]
}
