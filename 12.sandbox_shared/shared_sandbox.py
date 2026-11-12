#!/usr/bin/env python3
"""Render the shared Hub values and task manifests, or operate an existing task."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


HERE = Path(__file__).resolve().parent
DNS = r"[a-z0-9](?:[a-z0-9-]{0,46}[a-z0-9])?"
ACCOUNT = r"[a-z0-9][a-z0-9._+-]*@[a-z0-9][a-z0-9.-]*\.[a-z]{2,}"
IMAGE = r"[a-z0-9-]+-docker\.pkg\.dev/[a-z0-9-]+/[a-z0-9-]+/[a-z0-9_./-]+@sha256:[0-9a-f]{64}"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_group(path):
    settings = json.loads(path.read_text())
    group = settings["group"]
    require(re.fullmatch(DNS, group), "group must be a DNS label")
    require(re.fullmatch(r"[a-z0-9-]+(?:\.[a-z0-9-]+)+", settings["domain"]), "invalid group DNS")
    require(re.fullmatch(DNS, settings.get("test_accounts_secret", "shared-test-accounts")),
            "invalid test-account Secret name")
    require(re.fullmatch(r"[a-z0-9-]+-docker\.pkg\.dev/[a-z0-9-]+/[a-z0-9-]+",
                         settings["platform_registry"]), "invalid platform AR repository")
    require(settings["tasks"], "at least one task is required")
    for name, task in settings["tasks"].items():
        require(re.fullmatch(DNS, name) and name != group, f"invalid task namespace: {name}")
        members = task["members"]
        require(len(members) == 5 and len(set(members)) == 5
                and all(len(member) <= 150 and re.fullmatch(ACCOUNT, member) for member in members),
                f"{name}: specify five unique lowercase test-account emails")
        home_dirs = task.get("home_dirs", {})
        require(set(home_dirs).issubset(members)
                and all(re.fullmatch(r"[a-zA-Z0-9_][a-zA-Z0-9_.@+-]{0,149}", home)
                        for home in home_dirs.values()),
                f"{name}: home_dirs must map approved accounts to relative directory names")
        require(len({home_dirs.get(member, member) for member in members}) == 5,
                f"{name}: member home directories must be distinct")
        require(re.fullmatch(IMAGE, task["image"]), f"{name}: an AR image digest is required")
        require(re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]@[a-z][a-z0-9-]{4,28}[a-z0-9]\.iam\.gserviceaccount\.com",
                             task["gsa"]), f"{name}: specify a dedicated task GSA email")
        storage = task["storage"]
        require(re.fullmatch(DNS, storage["claim"]), f"{name}: invalid PVC name")
        if "storage_class" in storage:
            require(re.fullmatch(DNS, storage["storage_class"]), f"{name}: invalid StorageClass")
            require(re.fullmatch(r"[1-9][0-9]*Gi", storage.get("capacity", "100Gi")),
                    f"{name}: specify capacity in whole Gi")
        require(all(type(task.get(key, default)) is int and task.get(key, default) > 0
                    for key, default in (("uid", 1000), ("gid", 100))),
                f"{name}: uid and gid must be positive integers")
        if "sub_path" in storage:
            require(re.fullmatch(r"[a-z0-9_-]+(?:/[a-z0-9_-]+)*", storage["sub_path"]),
                    f"{name}: use a relative Filestore directory")
    require(len({task["gsa"] for task in settings["tasks"].values()}) == len(settings["tasks"]),
            "each task in the group requires a distinct GSA")
    return settings


def member_secret(member):
    return "notebook-session-" + hashlib.sha256(member.encode()).hexdigest()[:24]


def member_ports(start):
    return [{"port": port, "protocol": "TCP"} for port in range(start, start + 5)]


def group_values(settings):
    registry = settings["platform_registry"]
    members = {name: task["members"] for name, task in settings["tasks"].items()}
    config = (
        f"SHARED_TASKS = {members!r}\n"
        f"GROUP_NAMESPACE = {settings['group']!r}\n"
        + (HERE / "hub_spawner.py").read_text()
    )
    task_peer = {"namespaceSelector": {"matchLabels": {"sandbox-group": settings["group"]}},
                 "podSelector": {"matchLabels": {"app": "shared-notebook"}}}
    test_accounts_secret = settings.get("test_accounts_secret", "shared-test-accounts")
    return {
        "hub": {
            "serviceAccount": {"name": "shared-hub"},
            "image": {"name": f"{registry}/jupyterhub-k8s-hub", "tag": "4.2.0"},
            "extraVolumes": [{
                "name": "test-accounts", "secret": {
                    "secretName": test_accounts_secret, "items": [{"key": "accounts.json", "path": "accounts.json"}],
                },
            }],
            "extraVolumeMounts": [{
                "name": "test-accounts", "mountPath": "/etc/jupyterhub/test-accounts", "readOnly": True,
            }],
            "extraConfig": {
                "40-test-passwords": (HERE / "test_passwords.py").read_text(),
                "50-shared-sandbox": config,
            },
            "networkPolicy": {
                "ingress": [{"from": [task_peer], "ports": [{"port": 8081}]}],
                "egress": [{"to": [task_peer], "ports": member_ports(8888) + member_ports(9000)}],
            },
        },
        "proxy": {
            "service": {"type": "ClusterIP",
                        "annotations": {"cloud.google.com/neg": '{"exposed_ports":{"80":{}}}'}},
            "chp": {
                "image": {"name": f"{registry}/jupyterhub-configurable-http-proxy", "tag": "4.6.3"},
                "networkPolicy": {
                    "egress": [{"to": [task_peer], "ports": member_ports(8888)}],
                },
            },
        },
        "singleuser": {"networkPolicy": {"enabled": False}},
        "prePuller": {"hook": {"enabled": False}, "continuous": {"enabled": False}},
        "scheduling": {"userScheduler": {"enabled": False}},
        "cull": {"enabled": True, "timeout": 3600, "removeNamedServers": True},
    }


def resource(api, kind, name, namespace=None, **fields):
    metadata = {"name": name}
    if namespace:
        metadata["namespace"] = namespace
    return {"apiVersion": api, "kind": kind, "metadata": metadata, **fields}


def task_resources(settings, name):
    task = settings["tasks"][name]
    group = settings["group"]
    storage = task["storage"]
    labels = {"app": "shared-notebook"}
    role_api = "rbac.authorization.k8s.io"
    ksa = f"ksa-jupyter-{name}"
    namespace = resource("v1", "Namespace", name)
    namespace["metadata"]["labels"] = {"sandbox-group": group}
    account = resource("v1", "ServiceAccount", ksa, name)
    account["metadata"]["annotations"] = {"iam.gke.io/gcp-service-account": task["gsa"]}
    items = [namespace, account]
    if "storage_class" in storage:
        items.append(resource("v1", "PersistentVolumeClaim", storage["claim"], name, spec={
            "accessModes": ["ReadWriteMany"], "storageClassName": storage["storage_class"],
            "resources": {"requests": {"storage": storage.get("capacity", "100Gi")}},
        }))

    secrets = [member_secret(member) for member in task["members"]]
    items.extend(resource("v1", "Secret", secret, name, type="Opaque") for secret in secrets)
    items.extend([
        resource(f"{role_api}/v1", "Role", "shared-hub-sessions", name, rules=[{
            "apiGroups": [""], "resources": ["secrets"], "resourceNames": secrets, "verbs": ["patch"],
        }]),
        resource(f"{role_api}/v1", "RoleBinding", "shared-hub-sessions", name,
                 roleRef={"apiGroup": role_api, "kind": "Role", "name": "shared-hub-sessions"},
                 subjects=[{"kind": "ServiceAccount", "name": "shared-hub", "namespace": group}]),
        resource("v1", "ConfigMap", "notebook-slot", name,
                 data={"notebook_slot.py": (HERE / "notebook_slot.py").read_text()}),
    ])

    containers = []
    volumes = [{"name": "home", "persistentVolumeClaim": {"claimName": storage["claim"]}},
               {"name": "launcher", "configMap": {"name": "notebook-slot"}}]
    ports = []
    for index, member in enumerate(task["members"]):
        slot = f"member-{index}"
        home_dir = task.get("home_dirs", {}).get(member, member)
        notebook_port, status_port = 8888 + index, 9000 + index
        ports.extend([{"name": f"web-{index}", "port": notebook_port},
                      {"name": f"status-{index}", "port": status_port}])
        home = {"name": "home", "mountPath": "/home/jupyter"}
        if "sub_path" in storage:
            home["subPath"] = storage["sub_path"]
        volumes.append({"name": slot, "secret": {"secretName": secrets[index], "optional": True}})
        allocation = {"cpu": "1600m", "memory": f"{13108 if index == 4 else 13107}Mi",
                      "ephemeral-storage": "2Gi"}
        containers.append({
            "name": slot, "image": task["image"], "command": ["python", "/launcher/notebook_slot.py"],
            "workingDir": "/home/jupyter",
            "env": [{"name": "HOME", "value": f"/home/jupyter/{home_dir}"},
                    {"name": "NOTEBOOK_PORT", "value": str(notebook_port)}],
            "volumeMounts": [home, {"name": slot, "mountPath": "/var/run/notebook-session", "readOnly": True},
                             {"name": "launcher", "mountPath": "/launcher", "readOnly": True}],
            "resources": {"requests": allocation, "limits": allocation},
            "readinessProbe": {"httpGet": {"path": "/live", "port": status_port}},
            "securityContext": {"allowPrivilegeEscalation": False, "capabilities": {"drop": ["ALL"]}},
        })
    uid = task.get("uid", 1000)
    gid = task.get("gid", 100)
    template = {
        "metadata": {"labels": labels},
        "spec": {
            "serviceAccountName": ksa, "automountServiceAccountToken": False,
            "nodeSelector": {"cloud.google.com/compute-class": "Balanced"},
            "securityContext": {"runAsNonRoot": True, "runAsUser": uid, "runAsGroup": gid,
                                "fsGroup": gid, "seccompProfile": {"type": "RuntimeDefault"}},
            "containers": containers, "volumes": volumes,
        },
    }
    group_namespace = {"matchLabels": {"kubernetes.io/metadata.name": group}}
    items.extend([
        resource("apps/v1", "Deployment", "notebook", name, spec={
            # Creation defaults to one replica. Omit replicas on re-apply so a
            # portal stop (scale to zero) remains effective during reconciliation.
            "strategy": {"type": "Recreate"}, "selector": {"matchLabels": labels},
            "template": template,
        }),
        resource("v1", "Service", "notebook", name, spec={"selector": labels, "ports": ports}),
        resource("networking.k8s.io/v1", "NetworkPolicy", "group-hub-and-proxy", name, spec={
            "podSelector": {"matchLabels": labels}, "policyTypes": ["Ingress"],
            "ingress": [
                {"from": [{"namespaceSelector": group_namespace,
                           "podSelector": {"matchLabels": {"component": component}}}],
                 "ports": member_ports(start)}
                for component, start in (("hub", 9000), ("hub", 8888), ("proxy", 8888))
            ],
        }),
    ])
    return {"apiVersion": "v1", "kind": "List", "items": items}


def kubectl(context, namespace, *args):
    subprocess.run(["kubectl", "--context", context, "-n", namespace, *args], check=True)


def reconcile_alb(settings, args):
    sys.path.insert(0, str(HERE.parent / "09.sandbox_gke_deployer"))
    import reconcile_postdeploy as alb

    group = settings["group"]
    env = {**os.environ, "GCP_REGION": args.region}
    backends = alb.resolve_neg_backends(
        {"gke": {"namespace": group, "project_id": args.project}}, env, context=args.context
    )
    health_check = alb.ensure_health_check(args.project, group, env)
    backend = alb.ensure_backend_service(args.project, group, health_check, backends, env)
    alb.wait_for_backend_healthy(args.project, backend, env)
    alb.reconcile_url_map(args.project, args.url_map, group, settings["domain"], backend, env)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("group_json", type=Path)
    parser.add_argument("action", choices=["hub-values", "task-manifest", "alb", "start", "stop"])
    parser.add_argument("task", nargs="?")
    parser.add_argument("--context")
    parser.add_argument("--project")
    parser.add_argument("--region")
    parser.add_argument("--url-map")
    args = parser.parse_args()
    settings = load_group(args.group_json)
    if args.action == "hub-values":
        print(json.dumps(group_values(settings), indent=2))
        return
    if args.action == "alb":
        require(all((args.context, args.project, args.region, args.url_map)),
                "alb requires --context, --project, --region and --url-map")
        reconcile_alb(settings, args)
        return
    require(args.task in settings["tasks"], "specify a task from the group file")
    if args.action == "task-manifest":
        print(json.dumps(task_resources(settings, args.task), indent=2))
        return
    require(args.context, "--context is required for start and stop")
    if args.action == "start":
        kubectl(args.context, args.task, "scale", "deployment/notebook", "--replicas=1")
        kubectl(args.context, args.task, "rollout", "status", "deployment/notebook", "--timeout=10m")
    else:
        kubectl(args.context, args.task, "scale", "deployment/notebook", "--replicas=0")
        for member in settings["tasks"][args.task]["members"]:
            kubectl(args.context, args.task, "patch", "secret", member_secret(member),
                    "--type=merge", "-p", '{"data":{"session.json":null}}')


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError) as error:
        raise SystemExit(str(error))
