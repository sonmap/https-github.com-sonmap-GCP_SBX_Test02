#!/usr/bin/env bash
set -euo pipefail
command -v gcloud
gcloud auth list
gcloud config get-value project
echo 'Read 02.sandbox_setup_01_gcloud/00-variables.md and run the commands in 01-admin.md, 02-network.md, 03-foundation.md one at a time.'
