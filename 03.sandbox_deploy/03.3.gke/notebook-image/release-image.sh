#!/usr/bin/env bash
set -euo pipefail

if [[ $# != 2 ]]; then
  echo "Usage: release-image.sh AR_IMAGE@sha256:DIGEST UNIQUE_RELEASE_TAG" >&2
  exit 2
fi
image=$1
tag=$2
if [[ ! "$image" =~ ^[a-z0-9-]+-docker\.pkg\.dev/[a-z0-9-]+/[a-z0-9-]+/[a-z0-9_./-]+@sha256:[0-9a-f]{64}$ ||
      ! "$tag" =~ ^[a-z0-9][a-z0-9_.-]{0,127}$ || "$tag" == latest ]]; then
  echo "Use an approved AR digest and a unique version tag." >&2
  exit 2
fi

repository_image=${image%@*}
target="$repository_image:$tag"
digest=${image##*@}

tag_digest() {
  gcloud artifacts docker tags list "$repository_image" --format='value(tag.basename(),version.basename())' |
    awk -v tag="$tag" '$1 == tag { print $2 }'
}

current=$(tag_digest)
if [[ -n "$current" && "$current" != "$digest" ]]; then
  echo "Release tag already refers to another digest: $target" >&2
  exit 1
fi
if [[ -z "$current" ]]; then
  gcloud artifacts docker tags add "$image" "$target" --quiet
fi
if [[ "$(tag_digest)" != "$digest" ]]; then
  echo "Published digest does not match the approved digest: $target" >&2
  exit 1
fi
printf '%s\n' "$target"
