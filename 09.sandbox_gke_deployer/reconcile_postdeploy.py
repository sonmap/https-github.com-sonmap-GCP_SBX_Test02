#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


ZONAL_NEG_RE = re.compile(r"/zones/([^/]+)/networkEndpointGroups/([^/]+)$")


def run(args, *, env=None, quiet=False):
    command = " ".join(args)
    if not quiet:
        print(f"[RUN] {command}", flush=True)
    result = subprocess.run(
        args,
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


def gcloud(*args, env=None, quiet=False):
    return run(["gcloud", *args], env=env, quiet=quiet)


def gcloud_describe_or_none(resource_args, *, env=None):
    args = ["gcloud", *resource_args, "--format=json"]
    result = subprocess.run(
        args,
        text=True,
        check=False,
        capture_output=True,
        env=env,
    )
    if result.returncode == 0:
        return json.loads(result.stdout or "{}")
    text = f"{result.stdout}\n{result.stderr}".lower()
    if "not found" in text or "was not found" in text:
        return None
    raise RuntimeError(
        f"command failed ({result.returncode}): {' '.join(args)}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


def expected_backend(path_matcher, backend_uri):
    service = path_matcher.get("defaultService", "")
    return service == backend_uri or service.endswith("/" + backend_uri)



def verify_workload_identity(request, env):
    task = request["task"]["name"]
    namespace = request["gke"]["namespace"]
    ksa = f"ksa-jupyter-{task}"
    expected_gsa = (
        f"gsa-jupyter-{task}@{request['project']['project_id']}.iam.gserviceaccount.com"
        if request["identity"].get("create_jupyter_gsa", False)
        else f"sbx-manager@{os.environ['SBX_GKE_PROJECT']}.iam.gserviceaccount.com"
    )
    actual_gsa = run([
        "kubectl", "get", "serviceaccount", ksa,
        f"--namespace={namespace}",
        "--output=jsonpath={.metadata.annotations.iam\\.gke\\.io/gcp-service-account}",
    ], env=env)
    if actual_gsa != expected_gsa:
        raise RuntimeError(
            f"KSA/GSA mismatch: {namespace}/{ksa} -> {actual_gsa!r}, "
            f"expected {expected_gsa!r}"
        )
    print(
        f"[OK] Workload Identity: {namespace}/{ksa} -> {expected_gsa}",
        flush=True,
    )


def resolve_neg_backends(request, env):
    namespace = request["gke"]["namespace"]
    gke_project = request["gke"]["project_id"]
    last_status = None

    for _ in range(30):
        svcnegs = json.loads(run([
            "kubectl", "get", "svcneg",
            f"--namespace={namespace}", "--output=json",
        ], env=env, quiet=True))

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
            ], env=env, quiet=True))
            raw_status = service.get("metadata", {}).get("annotations", {}).get(
                "cloud.google.com/neg-status"
            )
            if raw_status:
                last_status = json.loads(raw_status)
                neg_name = last_status.get("network_endpoint_groups", {}).get("80")
                zones = last_status.get("zones", [])
                if neg_name and zones:
                    backends = []
                    for zone in zones:
                        backends.append({
                            "name": neg_name,
                            "zone": zone,
                            "self_link": (
                                f"projects/{gke_project}/zones/{zone}/"
                                f"networkEndpointGroups/{neg_name}"
                            ),
                        })
                    print(
                        f"[OK] Standalone NEG ready: {neg_name} zones={','.join(zones)}",
                        flush=True,
                    )
                    return backends
        time.sleep(10)

    raise RuntimeError(
        "GKE NEG for proxy-public did not reach Synced=True with a valid status "
        f"within 5 minutes; last_status={last_status}"
    )


def ensure_health_check(project, task, env):
    name = f"hc-jupyter-{task}"
    describe_args = (
        "compute", "health-checks", "describe", name,
        f"--project={project}", f"--region={env['GCP_REGION']}",
    )
    current = gcloud_describe_or_none(describe_args, env=env)
    if current is None:
        gcloud(
            "compute", "health-checks", "create", "http", name,
            f"--project={project}", f"--region={env['GCP_REGION']}",
            "--request-path=/_chp_healthz",
            "--check-interval=10s",
            "--timeout=5s",
            "--use-serving-port",
            "--quiet",
            env=env,
        )
        print(f"[OK] Created health check {name}", flush=True)
    else:
        gcloud(
            "compute", "health-checks", "update", "http", name,
            f"--project={project}", f"--region={env['GCP_REGION']}",
            "--request-path=/_chp_healthz",
            "--check-interval=10s",
            "--timeout=5s",
            "--use-serving-port",
            "--quiet",
            env=env,
        )
        print(f"[OK] Reused health check {name}", flush=True)
    return name


def ensure_backend_service(project, task, health_check_name, neg_backends, env):
    name = f"bes-jupyter-{task}"
    describe_args = (
        "compute", "backend-services", "describe", name,
        f"--project={project}", f"--region={env['GCP_REGION']}",
    )
    current = gcloud_describe_or_none(describe_args, env=env)

    if current is None:
        gcloud(
            "compute", "backend-services", "create", name,
            f"--project={project}", f"--region={env['GCP_REGION']}",
            "--load-balancing-scheme=INTERNAL_MANAGED",
            "--protocol=HTTP",
            "--timeout=30s",
            f"--health-checks={health_check_name}",
            f"--health-checks-region={env['GCP_REGION']}",
            "--quiet",
            env=env,
        )
        current = gcloud_describe_or_none(describe_args, env=env)
        print(f"[OK] Created backend service {name}", flush=True)
    else:
        if current.get("loadBalancingScheme") != "INTERNAL_MANAGED":
            raise RuntimeError(
                f"backend {name} has unexpected loadBalancingScheme="
                f"{current.get('loadBalancingScheme')}"
            )
        if current.get("protocol") != "HTTP":
            raise RuntimeError(
                f"backend {name} has unexpected protocol={current.get('protocol')}"
            )
        gcloud(
            "compute", "backend-services", "update", name,
            f"--project={project}", f"--region={env['GCP_REGION']}",
            "--timeout=30s",
            f"--health-checks={health_check_name}",
            f"--health-checks-region={env['GCP_REGION']}",
            "--quiet",
            env=env,
        )
        current = gcloud_describe_or_none(describe_args, env=env)
        print(f"[OK] Reused backend service {name}", flush=True)

    desired = {item["self_link"] for item in neg_backends}
    attached = {
        backend.get("group")
        for backend in current.get("backends", [])
        if backend.get("group")
    }

    # This backend service is task-dedicated, so remove stale zonal NEGs left
    # by a previous GKE/NEG generation before attaching the current NEG set.
    for group in sorted(attached - desired):
        match = ZONAL_NEG_RE.search(group)
        if not match:
            raise RuntimeError(f"unexpected backend group on {name}: {group}")
        zone, neg_name = match.groups()
        gcloud(
            "compute", "backend-services", "remove-backend", name,
            f"--project={project}", f"--region={env['GCP_REGION']}",
            f"--network-endpoint-group={neg_name}",
            f"--network-endpoint-group-zone={zone}",
            "--quiet",
            env=env,
        )
        print(f"[OK] Removed stale NEG backend {zone}/{neg_name}", flush=True)

    for backend in neg_backends:
        if backend["self_link"] in attached:
            continue
        gcloud(
            "compute", "backend-services", "add-backend", name,
            f"--project={project}", f"--region={env['GCP_REGION']}",
            f"--network-endpoint-group={backend['name']}",
            f"--network-endpoint-group-zone={backend['zone']}",
            "--balancing-mode=RATE",
            "--max-rate-per-endpoint=100",
            "--capacity-scaler=1.0",
            "--quiet",
            env=env,
        )
        print(
            f"[OK] Attached NEG backend {backend['zone']}/{backend['name']}",
            flush=True,
        )

    return name


def wait_for_backend_healthy(project, backend_name, env):
    last_states = []
    for _ in range(30):
        raw = gcloud(
            "compute", "backend-services", "get-health", backend_name,
            f"--project={project}", f"--region={env['GCP_REGION']}", "--format=json",
            env=env, quiet=True,
        )
        payload = json.loads(raw or "[]")
        states = []
        for entry in payload:
            for health in entry.get("status", {}).get("healthStatus", []):
                states.append(health.get("healthState", "UNKNOWN"))
        last_states = states
        if "HEALTHY" in states:
            print(f"[OK] Backend {backend_name} HEALTHY: {states}", flush=True)
            return
        time.sleep(10)
    raise RuntimeError(
        f"backend {backend_name} did not become HEALTHY within 5 minutes; "
        f"last health states={last_states}"
    )


def reconcile_url_map(project, url_map_name, task, hostname, backend_name, env):
    backend_uri = f"projects/{project}/regions/{env['GCP_REGION']}/backendServices/{backend_name}"
    raw = gcloud(
        "compute", "url-maps", "describe", url_map_name,
        f"--project={project}", f"--region={env['GCP_REGION']}", "--format=json", env=env,
    )
    config = json.loads(raw)

    path_matchers = {
        item.get("name"): item
        for item in config.get("pathMatchers", [])
        if item.get("name")
    }
    current_matcher = path_matchers.get(task)
    if current_matcher is None:
        gcloud(
            "compute", "url-maps", "add-path-matcher", url_map_name,
            f"--project={project}", f"--region={env['GCP_REGION']}",
            f"--path-matcher-name={task}",
            f"--default-service={backend_uri}",
            env=env,
        )
    elif not expected_backend(current_matcher, backend_uri):
        raise RuntimeError(
            f"URL map path matcher {task} already exists but does not point to "
            f"{backend_name}: {current_matcher.get('defaultService')}"
        )

    raw = gcloud(
        "compute", "url-maps", "describe", url_map_name,
        f"--project={project}", f"--region={env['GCP_REGION']}", "--format=json", env=env,
    )
    config = json.loads(raw)
    hostname_rules = [
        item for item in config.get("hostRules", [])
        if hostname in item.get("hosts", [])
    ]
    if not hostname_rules:
        gcloud(
            "compute", "url-maps", "add-host-rule", url_map_name,
            f"--project={project}", f"--region={env['GCP_REGION']}",
            f"--hosts={hostname}",
            f"--path-matcher-name={task}",
            env=env,
        )
    elif any(item.get("pathMatcher") != task for item in hostname_rules):
        raise RuntimeError(
            f"hostname {hostname} is already registered to a different path matcher: "
            f"{hostname_rules}"
        )

    raw = gcloud(
        "compute", "url-maps", "describe", url_map_name,
        f"--project={project}", f"--region={env['GCP_REGION']}", "--format=json", env=env,
    )
    config = json.loads(raw)
    path_matchers = {
        item.get("name"): item
        for item in config.get("pathMatchers", [])
        if item.get("name")
    }
    matcher = path_matchers.get(task)
    host_ok = any(
        hostname in item.get("hosts", []) and item.get("pathMatcher") == task
        for item in config.get("hostRules", [])
    )
    if matcher is None or not expected_backend(matcher, backend_uri) or not host_ok:
        raise RuntimeError(
            f"URL map reconciliation failed for {hostname} -> {backend_name}"
        )
    print(f"[OK] URL map route: {hostname} -> {backend_name}", flush=True)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: reconcile_postdeploy.py APPROVED_REQUEST_JSON")

    request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    task = request["task"]["name"]
    gke = request["gke"]
    sandbox_project = os.environ["SBX_GKE_PROJECT"]
    url_map_name = os.environ.get(
        "SHARED_URL_MAP_NAME", "urlmap-alb-sbxtest01-shared"
    )

    # Both Kubernetes and load-balancer operations run as tf-manager.
    gke_env = dict(os.environ)
    gke_env.pop("CLOUDSDK_AUTH_IMPERSONATE_SERVICE_ACCOUNT", None)
    verify_workload_identity(request, gke_env)
    neg_backends = resolve_neg_backends(request, gke_env)

    # Foundation already owns the shared ALB. Per-task provisioning only adds
    # HC + backend service + NEG attachment + URL-map host/path route.
    lb_env = dict(os.environ)
    lb_env.pop("CLOUDSDK_AUTH_IMPERSONATE_SERVICE_ACCOUNT", None)
    health_check_name = ensure_health_check(gke["project_id"], task, lb_env)
    backend_name = ensure_backend_service(
        gke["project_id"], task, health_check_name, neg_backends, lb_env
    )
    wait_for_backend_healthy(gke["project_id"], backend_name, lb_env)
    reconcile_url_map(
        gke["project_id"],
        url_map_name,
        task,
        gke["jupyter_domain"],
        backend_name,
        lb_env,
    )
    print(f"[OK] Sandbox {task} ALB attachment complete", flush=True)


if __name__ == "__main__":
    main()
