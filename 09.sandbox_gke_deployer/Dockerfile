FROM gcr.io/google.com/cloudsdktool/cloud-sdk:slim

ARG HELM_VERSION=v3.16.2

COPY 09.sandbox_gke_deployer/requirements.txt /tmp/requirements.txt
COPY 09.sandbox_gke_deployer/apply_gke_workload.py /opt/sandbox/apply_gke_workload.py
COPY 09.sandbox_gke_deployer/reconcile_postdeploy.py /opt/sandbox/reconcile_postdeploy.py

COPY 12.sandbox_shared/shared_sandbox.py 12.sandbox_shared/hub_spawner.py 12.sandbox_shared/notebook_slot.py 12.sandbox_shared/test_passwords.py /opt/sandbox/12.sandbox_shared/
COPY 09.sandbox_gke_deployer/deploy_shared_group.py /opt/sandbox/deploy_shared_group.py

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl kubectl python3-pip skopeo google-cloud-cli-gke-gcloud-auth-plugin \
    && pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt \
    && curl -fsSLo /tmp/helm.tar.gz "https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz" \
    && tar -xzf /tmp/helm.tar.gz -C /tmp \
    && install /tmp/linux-amd64/helm /usr/local/bin/helm \
    && chmod 0555 /opt/sandbox/apply_gke_workload.py /opt/sandbox/reconcile_postdeploy.py \
    && rm -rf /var/lib/apt/lists/* /tmp/helm.tar.gz /tmp/linux-amd64 /tmp/requirements.txt
