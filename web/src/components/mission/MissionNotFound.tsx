import { Link } from 'react-router-dom'
import { CenteredState } from './CenteredState'
import { OUTLINE_PILL } from './pill'

export function MissionNotFound() {
  return (
    <CenteredState title="Mission not found" level={1}>
      <p className="text-sm text-muted">It may have been removed, or the link is wrong.</p>
      <Link to="/" className={`${OUTLINE_PILL} mt-3 px-4 py-1.5`}>
        Start a new mission
      </Link>
    </CenteredState>
  )
}
