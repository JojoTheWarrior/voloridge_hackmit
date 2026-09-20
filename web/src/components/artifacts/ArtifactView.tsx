import type { Artifact } from '../../types'

/** Renders one artifact in the mission thread. Unknown types render nothing. */
export function ArtifactView({ artifact }: { artifact: Artifact }) {
  void artifact
  return null
}
