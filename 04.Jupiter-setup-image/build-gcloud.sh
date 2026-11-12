#!/usr/bin/env bash
set -euo pipefail
SBX_GKE_PROJECT="${SBX_GKE_PROJECT:-gcp-sbx-edp-gke01}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

REGION="${REGION:-asia-northeast3}"
REPOSITORY="${REPOSITORY:-ar-sbxtest01-platform}"
IMAGE_NAME="${IMAGE_NAME:-jupyterhub-k8s-singleuser-standard}"
IMAGE_TAG="${IMAGE_TAG:-4.2.0-r2-home}"
BASE_IMAGE="${BASE_IMAGE:-${REGION}-docker.pkg.dev/${SBX_GKE_PROJECT}/${REPOSITORY}/jupyterhub-k8s-singleuser-sample:4.2.0}"
IMAGE_REPO="${REGION}-docker.pkg.dev/${SBX_GKE_PROJECT}/${REPOSITORY}/${IMAGE_NAME}"

# Existing regional staging bucket reused by the validated manual build.
# Override STAGING_BUCKET if a dedicated Jupyter build bucket is created later.
STAGING_BUCKET="${STAGING_BUCKET:-gcp-sbx-edp-gke01-sbxtest01-build-source}"
BUILD_SA="${BUILD_SA:-tf-manager@${SBX_GKE_PROJECT}.iam.gserviceaccount.com}"

BUCKET_LOCATION="$(gcloud storage buckets describe "gs://${STAGING_BUCKET}" --format='value(location)')"
if [[ "${BUCKET_LOCATION,,}" != "${REGION,,}" ]]; then
  echo "ERROR: gs://${STAGING_BUCKET} location=${BUCKET_LOCATION}; expected ${REGION}" >&2
  echo "This prevents constraints/gcp.resourceLocations HTTP 412 failures." >&2
  exit 1
fi

echo "[1/4] Grant Cloud Build source read access"
gcloud storage buckets add-iam-policy-binding \
  "gs://${STAGING_BUCKET}" \
  --member="serviceAccount:${BUILD_SA}" \
  --role="roles/storage.objectViewer" \
  --quiet

echo "[2/4] Submit regional Cloud Build"
gcloud builds submit "${SCRIPT_DIR}" \
  --project="${SBX_GKE_PROJECT}" \
  --region="${REGION}" \
  --service-account="projects/${SBX_GKE_PROJECT}/serviceAccounts/${BUILD_SA}" \
  --gcs-source-staging-dir="gs://${STAGING_BUCKET}/jupyter-source" \
  --config="${SCRIPT_DIR}/cloudbuild.yaml" \
  --substitutions="_BASE_IMAGE=${BASE_IMAGE},_IMAGE_REPO=${IMAGE_REPO},_IMAGE_TAG=${IMAGE_TAG}"

echo "[3/4] Verify image"
gcloud artifacts docker images describe \
  "${IMAGE_REPO}:${IMAGE_TAG}" \
  --project="${SBX_GKE_PROJECT}"

echo "[4/4] Done"
echo "IMAGE=${IMAGE_REPO}:${IMAGE_TAG}"
