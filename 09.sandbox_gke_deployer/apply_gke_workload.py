#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def run(args, *, input_text=None, env=None):
    command = " ".join(args)
    print(f"[RUN] {command}", flush=True)
    result = subprocess.run(
        args,
        input=input_text,
        text=True,
        check=False,
        capture_output=True,
        env=env,
    )
    if result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {command}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result.stdout.strip()


def gcloud(*args, env=None):
    return run(["gcloud", *args], env=env)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply_gke_workload.py APPROVED_REQUEST_GCS_URI")

    request_file = Path("/workspace/approved-request.json")
    gcloud("storage", "cp", sys.argv[1], str(request_file))
    request = json.loads(request_file.read_text(encoding="utf-8"))

    task = request["task"]["name"]
    group = request["identity"]["group_email"]
    gke = request["gke"]
    project = os.environ["SBX_GKE_PROJECT"]
    region = os.environ["GCP_REGION"]

    # The shared ALB itself is Foundation-owned. This step owns only the
    # Kubernetes/JupyterHub workload and the standalone NEG attachment.
    # Backend service, health check, and URL-map route are reconciled by
    # reconcile_postdeploy.py after this step completes.
    kubeconfig = Path("/workspace/kubeconfig")
    child_env = dict(os.environ)
    child_env["KUBECONFIG"] = str(kubeconfig)
    child_env.pop("CLOUDSDK_AUTH_IMPERSONATE_SERVICE_ACCOUNT", None)

    gcloud(
        "container", "clusters", "get-credentials", gke["cluster_name"],
        f"--project={gke['project_id']}",
        f"--location={gke['location']}",
        "--dns-endpoint" if os.environ.get("GKE_ENDPOINT_MODE", "internal") == "dns" else "--internal-ip",
        env=child_env,
    )

    # Read all required runtime secrets before changing Kubernetes resources.
    client_id = gcloud(
        "secrets", "versions", "access", "latest",
        "--secret=jupyter-oauth-client-id", f"--project={project}"
    )
    client_secret = gcloud(
        "secrets", "versions", "access", "latest",
        "--secret=jupyter-oauth-client-secret", f"--project={project}"
    )

    # Authenticate and confirm that the pinned OCI chart exists before
    # changing Kubernetes resources.
    registry = f"{region}-docker.pkg.dev"
    access_token = gcloud("auth", "print-access-token")
    run(
        ["helm", "registry", "login", registry, "--username", "oauth2accesstoken",
         "--password-stdin"],
        input_text=access_token,
        env=child_env,
    )
    run([
        "helm", "show", "chart", os.environ["JUPYTER_CHART_URI"],
        f"--version={os.environ['JUPYTER_CHART_VERSION']}",
    ], env=child_env)

    namespace = gke["namespace"]
    ksa = f"ksa-jupyter-{task}"
    jupyter_gsa = (
        f"gsa-jupyter-{task}@{request['project']['project_id']}.iam.gserviceaccount.com"
        if request["identity"].get("create_jupyter_gsa", False)
        else f"sbx-manager@{project}.iam.gserviceaccount.com"
    )
    manifest = {
        "apiVersion": "v1",
        "kind": "List",
        "items": [
            {
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": {
                    "name": namespace,
                    "labels": {
                        "sandbox/task": task,
                        "app.kubernetes.io/managed-by": "cloud-build",
                    },
                },
            },
            {
                "apiVersion": "v1",
                "kind": "ResourceQuota",
                "metadata": {"name": f"quota-{task}", "namespace": namespace},
                "spec": {"hard": {
                    "requests.cpu": "8",
                    "requests.memory": "64Gi",
                    "limits.cpu": "12",
                    "limits.memory": "96Gi",
                    "persistentvolumeclaims": "5",
                }},
            },
            {
                "apiVersion": "v1",
                "kind": "ServiceAccount",
                "metadata": {
                    "name": ksa,
                    "namespace": namespace,
                    "annotations": {"iam.gke.io/gcp-service-account": jupyter_gsa},
                },
            },
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "Role",
                "metadata": {"name": f"role-{task}-user", "namespace": namespace},
                "rules": [
                    {
                        "apiGroups": [""],
                        "resources": [
                            "pods", "pods/log", "services", "configmaps",
                            "persistentvolumeclaims",
                        ],
                        "verbs": ["get", "list", "watch", "create", "update", "patch", "delete"],
                    },
                    {
                        "apiGroups": ["apps"],
                        "resources": ["deployments"],
                        "verbs": ["get", "list", "watch", "create", "update", "patch", "delete"],
                    },
                ],
            },
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "RoleBinding",
                "metadata": {"name": f"rb-{task}-group", "namespace": namespace},
                "roleRef": {
                    "apiGroup": "rbac.authorization.k8s.io",
                    "kind": "Role",
                    "name": f"role-{task}-user",
                },
                "subjects": [{
                    "apiGroup": "rbac.authorization.k8s.io",
                    "kind": "Group",
                    "name": group,
                }],
            },
        ],
    }
    run(["kubectl", "apply", "-f", "-"], input_text=json.dumps(manifest), env=child_env)

    image_prefix = f"{region}-docker.pkg.dev/{project}/ar-sbxtest01-platform"
    singleuser_image = os.environ.get(
        "JUPYTER_SINGLEUSER_IMAGE",
        f"{image_prefix}/jupyterhub-k8s-singleuser-standard",
    )
    singleuser_image_tag = os.environ.get(
        "JUPYTER_SINGLEUSER_IMAGE_TAG",
        "4.2.0-r2-home",
    )
    allowed_users = [
        member.split("@", 1)[0]
        for member in request["identity"]["members"]
    ]

    values = {
        "hub": {
            "image": {
                "name": f"{image_prefix}/jupyterhub-k8s-hub",
                "tag": os.environ["JUPYTER_CHART_VERSION"],
            },
            "config": {
                "JupyterHub": {"authenticator_class": "google"},
                "Authenticator": {
                    "allow_all": False,
                    "allowed_users": allowed_users,
                },
                "GoogleOAuthenticator": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "oauth_callback_url": f"https://{gke['jupyter_domain']}/hub/oauth_callback",
                    "hosted_domain": ["sonmap.net"],
                    "strip_domain": True,
                    "login_service": "Sonmap Google Account",
                },
            },
            "resources": {
                "requests": {"cpu": "500m", "memory": "1Gi"},
                "limits": {"cpu": "1", "memory": "2Gi"},
            },
        },
        "proxy": {
            # GKE Autopilot requires at least 500m CPU request when a Pod uses
            # safe-to-evict=false. Protect the single CHP proxy from node
            # scale-down so the NEG does not temporarily lose its only endpoint.
            "annotations": {
                "cluster-autoscaler.kubernetes.io/safe-to-evict": "false",
            },
            "chp": {
                "image": {
                    "name": f"{image_prefix}/jupyterhub-configurable-http-proxy",
                    "tag": "4.6.3",
                },
                "resources": {
                    "requests": {"cpu": "500m", "memory": "512Mi"},
                    "limits": {"cpu": "500m", "memory": "1Gi"},
                },
            },
            "service": {"type": "ClusterIP"},
        },
        "singleuser": {
            "image": {
                "name": singleuser_image,
                "tag": singleuser_image_tag,
            },
            "serviceAccountName": ksa,
            "cpu": {"guarantee": 1, "limit": 2},
            "memory": {"guarantee": "8G", "limit": "16G"},
            "storage": {
                "type": "dynamic",
                "capacity": "40Gi",
                "dynamic": {"storageClass": "standard-rwo"},
            },
            "cloudMetadata": {"blockWithIptables": False},
            "networkPolicy": {
                "enabled": True,
                "egressAllowRules": {"cloudMetadataServer": True},
            },
        },
        "prePuller": {
            "hook": {"enabled": False},
            "continuous": {"enabled": False},
        },
        "scheduling": {"userScheduler": {"enabled": False}},
        "cull": {"enabled": True, "timeout": 3600},
    }
    # Only the standard image version with the startup script opts into
    # per-user homes. Explicit overrides to older/custom images keep their defaults.
    if (
        singleuser_image == f"{image_prefix}/jupyterhub-k8s-singleuser-standard"
        and singleuser_image_tag == "4.2.0-r2-home"
    ):
        notebook_home = "/home/{username}"
        values["singleuser"]["storage"]["homeMountPath"] = notebook_home
        values["singleuser"]["extraEnv"] = {"SANDBOX_NOTEBOOK_HOME": notebook_home}
        values["singleuser"]["cmd"] = ["/usr/local/bin/start-sandbox-notebook"]

    values_file = Path("/workspace/jupyter-values.json")
    values_file.write_text(json.dumps(values, indent=2), encoding="utf-8")

    run([
        "helm", "upgrade", "--install", f"jupyterhub-{task}",
        os.environ["JUPYTER_CHART_URI"],
        f"--version={os.environ['JUPYTER_CHART_VERSION']}",
        f"--namespace={namespace}",
        f"--values={values_file}",
        "--atomic", "--wait", "--timeout=15m",
    ], env=child_env)

    # Attach the standalone NEG only after Helm is healthy.
    neg_annotation = json.dumps(
        {"exposed_ports": {"80": {}}},
        separators=(",", ":"),
    )
    run([
        "kubectl", "annotate", "service", "proxy-public",
        f"--namespace={namespace}",
        f"cloud.google.com/neg={neg_annotation}",
        "--overwrite",
    ], env=child_env)

    # Wait only for GKE to materialize the NEG. No Infrastructure Manager/LB
    # deployment is performed here. The next Cloud Build step attaches this
    # NEG to the already-created shared ALB backend path.
    neg_status = None
    for _ in range(30):
        svcnegs = json.loads(run([
            "kubectl", "get", "svcneg",
            f"--namespace={namespace}", "--output=json",
        ], env=child_env))

        synced = False
        for item in svcnegs.get("items", []):
            labels = item.get("metadata", {}).get("labels", {})
            if (
                labels.get("networking.gke.io/service-name") != "proxy-public"
                or labels.get("networking.gke.io/service-port") != "80"
            ):
                continue
            conditions = item.get("status", {}).get("conditions", [])
            if any(
                condition.get("type") == "Synced"
                and condition.get("status") == "True"
                for condition in conditions
            ):
                synced = True
                break

        if synced:
            service = json.loads(run([
                "kubectl", "get", "service", "proxy-public",
                f"--namespace={namespace}", "--output=json",
            ], env=child_env))
            raw_status = service.get("metadata", {}).get("annotations", {}).get(
                "cloud.google.com/neg-status"
            )
            if raw_status:
                candidate = json.loads(raw_status)
                neg_name = candidate.get("network_endpoint_groups", {}).get("80")
                zones = candidate.get("zones", [])
                if neg_name and zones:
                    neg_status = candidate
                    break
        time.sleep(10)

    if not neg_status:
        raise RuntimeError(
            "GKE NEG for proxy-public did not reach Synced=True with a valid "
            "NEG status within 5 minutes"
        )

    neg_name = neg_status["network_endpoint_groups"]["80"]
    zones = neg_status["zones"]
    print(
        f"[OK] JupyterHub and standalone NEG ready: task={task} "
        f"neg={neg_name} zones={','.join(zones)}",
        flush=True,
    )


if __name__ == "__main__":
    main()
