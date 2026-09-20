import { ArtifactView } from './ArtifactView'
import { galleryArtifacts } from './galleryFixtures'

/** Dev-only page: one realistic example of every artifact type, for checking the visual system by eye. */
export function ArtifactGallery() {
  return (
    <div className="mx-auto flex w-full max-w-[720px] flex-col gap-6 px-4 py-10">
      {galleryArtifacts.map((artifact) => (
        <ArtifactView key={artifact.id} artifact={artifact} />
      ))}
    </div>
  )
}
