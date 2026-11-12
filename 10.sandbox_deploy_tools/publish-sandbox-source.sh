#!/usr/bin/env bash
set -euo pipefail

# Publish the approved Sandbox Terraform source from the VM to the
# internal GCS bundle bucket. Cloud Run consumes this immutable archive;
# it does not download Terraform source from GitHub.
#
# Usage:
#   ./10.sandbox_deploy_tools/publish-sandbox-source.sh BUCKET_NAME RELEASE_ID

bucket_name="${1:?Usage: $0 BUCKET_NAME RELEASE_ID}"
release_id="${2:?Usage: $0 BUCKET_NAME RELEASE_ID}"

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
source_root="$repo_root/08.sandbox_setup_02_terraform/deployments"
work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT

archive="$work_dir/sandbox-source.zip"
object="platform-releases/$release_id/sandbox-source.zip"

test -d "$source_root"
python3 - "$repo_root" "$archive" <<'PY'
import pathlib
import sys
import zipfile

repo_root = pathlib.Path(sys.argv[1])
archive = pathlib.Path(sys.argv[2])
source = repo_root / "08.sandbox_setup_02_terraform" / "deployments"

excluded_dirs = {".terraform", "__pycache__"}
excluded_names = {
    ".terraform.lock.hcl",
    ".terraform.tfstate.lock.info",
    "crash.log",
    "terraform.tfvars",
    "terraform.auto.tfvars.json",
}
excluded_suffixes = (".tfplan", ".tfstate", ".tfstate.backup")

with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if any(part in excluded_dirs for part in relative.parts):
            continue
        if not path.is_file():
            continue
        if path.name in excluded_names:
            continue
        if path.name.endswith(excluded_suffixes):
            continue
        if path.name.endswith(".auto.tfvars") or path.name.endswith(".auto.tfvars.json"):
            continue
        output.write(path, path.relative_to(repo_root))
PY

sha256="$(sha256sum "$archive" | awk '{print $1}')"
gcloud storage cp "$archive" "gs://$bucket_name/$object"

generation="$(gcloud storage objects describe "gs://$bucket_name/$object" --format='value(generation)')"

cat <<EOF
archive_uri=gs://$bucket_name/$object
generation=$generation
sha256=$sha256
EOF
