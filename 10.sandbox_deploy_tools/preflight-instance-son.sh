#!/usr/bin/env bash
set -euo pipefail
command -v gcloud
gcloud auth list
gcloud config get-value project
echo 'Follow the common variables and individual setup commands in 01.docs/01-infra-setup.md.'
