ARG BASE_IMAGE=asia-northeast3-docker.pkg.dev/gcp-sbx-edp-gke01/ar-sbxtest01-platform/jupyterhub-k8s-singleuser-sample:4.2.0
FROM ${BASE_IMAGE}

ARG IMAGE_VERSION=4.2.0-r2-home

USER root

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      git \
      gnupg \
      jq \
      unzip && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /usr/share/keyrings && \
    curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
      | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
      > /etc/apt/sources.list.d/google-cloud-sdk.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends google-cloud-cli && \
    rm -rf /var/lib/apt/lists/*

ARG NOTEBOOK_PIP_MODE=index
RUN --mount=type=bind,target=/build-inputs \
    case "${NOTEBOOK_PIP_MODE}" in \
      index) set -- ;; \
      wheelhouse) set -- --no-index --find-links=/build-inputs/wheelhouse --only-binary=:all: ;; \
      *) echo "NOTEBOOK_PIP_MODE must be index or wheelhouse" >&2; exit 2 ;; \
    esac && \
    python -m pip install --no-cache-dir "$@" -r /build-inputs/requirements.txt && \
    python -m pip check

RUN printf '%s\n' "sandbox-jupyter-standard ${IMAGE_VERSION}" > /etc/sandbox-image-version

COPY start-sandbox-notebook.sh /usr/local/bin/start-sandbox-notebook
RUN chmod 0755 /usr/local/bin/start-sandbox-notebook

USER jovyan
WORKDIR /home/jovyan
