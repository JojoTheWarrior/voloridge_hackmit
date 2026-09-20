#!/bin/sh
# Refresh this folder from the working research directory, leaving the data behind.
# Usage: research/sync_from_explore.sh [path-to-explore]   (default: ../explore, next to the repo)
set -eu
here="$(cd "$(dirname "$0")" && pwd)"
src="${1:-$here/../../explore}"
[ -d "$src" ] || { echo "no such directory: $src" >&2; exit 1; }
# Files over 1.5 MB are inputs that can be downloaded again, not findings.
rsync -a --delete --prune-empty-dirs --max-size=1500k \
  --filter="P /README.md" --filter="P /sync_from_explore.sh" --filter="P /.snapshot-filter" \
  --filter="P /library.json" --filter="- /library.json" \
  --filter="merge $here/.snapshot-filter" "$src"/ "$here"/
echo "synced $(find "$here" -type f | wc -l | tr -d ' ') files from $src"
