import type { Explorer } from '../../types'
import { explorerPath } from '../mission/paths'
import { DeliveryCard } from './DeliveryCard'

export function ExplorerCard({ missionId, explorer }: { missionId: string; explorer: Explorer }) {
  return <DeliveryCard label="Explorer" eyebrow="Explorer ready" title={explorer.title} summary={explorer.description} to={explorerPath(missionId)} action="Open explorer" />
}
