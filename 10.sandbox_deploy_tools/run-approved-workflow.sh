#!/usr/bin/env bash
# Upload one approved request JSON after validating its request_id, then invoke
# the provisioning Workflow with the exact object generation and SHA256.
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "Usage: bash 10.sandbox_deploy_tools/run-approved-workflow.sh REQUEST_ID APPROVED_JSON_FILE" >&2
  exit 2
fi

REQUEST_ID="$1"
APPROVED_JSON_FILE="$2"
SBX_GKE_PROJECT="${SBX_GKE_PROJECT:-gcp-sbx-edp-gke01}"
REGION="asia-northeast3"
WORKFLOW_NAME="workflow-sbxtest01-provision"
REQUEST_BUCKET="${SBX_GKE_PROJECT}-sbxtest01-requests"
REQUEST_URI="gs://${REQUEST_BUCKET}/approved/${REQUEST_ID}/request.json"

if ! [[ "${REQUEST_ID}" =~ ^REQ-[0-9]{8}-[0-9]{3}$ ]]; then
  echo "REQUEST_ID must use REQ-YYYYMMDD-NNN format." >&2
  exit 2
fi

if [ ! -f "${APPROVED_JSON_FILE}" ]; then
  echo "Approved JSON file was not found: ${APPROVED_JSON_FILE}" >&2
  exit 2
fi

JSON_REQUEST_ID="$(jq -r '.request_id // empty' "${APPROVED_JSON_FILE}")"
if [ "${JSON_REQUEST_ID}" != "${REQUEST_ID}" ]; then
  echo "JSON request_id (${JSON_REQUEST_ID:-missing}) must equal ${REQUEST_ID}." >&2
  exit 2
fi

gcloud storage cp "${APPROVED_JSON_FILE}" "${REQUEST_URI}"

REQUEST_GENERATION="$(gcloud storage objects describe "${REQUEST_URI}" --format="value(generation)")"
REQUEST_SHA256="$(gcloud storage cat "${REQUEST_URI}" | sha256sum | awk '{print $1}')"

if [ -z "${REQUEST_GENERATION}" ] || [ -z "${REQUEST_SHA256}" ]; then
  echo "Unable to read generation or SHA256 for ${REQUEST_URI}." >&2
  exit 1
fi

gcloud workflows run "${WORKFLOW_NAME}" \
  --project="${SBX_GKE_PROJECT}" \
  --location="${REGION}" \
  --data="$(jq -nc \
    --arg request_id "${REQUEST_ID}" \
    --arg approved_json_uri "${REQUEST_URI}" \
    --arg generation "${REQUEST_GENERATION}" \
    --arg sha256 "${REQUEST_SHA256}" \
    '{request_id:$request_id, approved_json_uri:$approved_json_uri, generation:($generation|tonumber), sha256:$sha256}')"
