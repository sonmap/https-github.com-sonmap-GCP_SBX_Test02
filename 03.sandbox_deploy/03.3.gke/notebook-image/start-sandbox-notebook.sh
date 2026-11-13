#!/bin/sh
set -eu

: "${SANDBOX_NOTEBOOK_HOME:?Notebook home was not configured}"
export HOME="$SANDBOX_NOTEBOOK_HOME"
cd "$HOME"
exec jupyterhub-singleuser "$@"
