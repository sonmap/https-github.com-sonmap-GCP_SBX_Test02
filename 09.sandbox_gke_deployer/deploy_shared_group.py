#!/usr/bin/env python3
"""Reconcile one complete approved group in a private Cloud Build pool."""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

from google.api_core.exceptions import PreconditionFailed
from google.cloud import storage

sys.path.insert(0, str(Path(__file__).resolve().parent / "12.sandbox_shared"))
sys.path.append(str(Path(__file__).resolve().parents[1] / "12.sandbox_shared"))
from shared_sandbox import DNS, group_values, load_group, member_secret, reconcile_alb, require, task_resources
from test_passwords import PASSWORD_HASH


OWNER_LABEL = "sandbox-group"


def run(*args, env, input_text=None, sensitive=False):
    result = subprocess.run(args, env=env, input=input_text, text=True, capture_output=True)
    if result.returncode:
        command = " ".join(args)
        details = "" if sensitive else f"\n{result.stderr.strip()}"
        raise RuntimeError(f"{command} failed ({result.returncode}){details}")
    return result.stdout


def reconcile(settings, config_dir, env):
    group = settings["group"]
    project = env["SBX_GKE_PROJECT"]
    region = env["GCP_REGION"]
    registry = env["JUPYTER_CHART_URI"].removeprefix("oci://").rsplit("/", 1)[0]
    require(settings["platform_registry"] == registry, "group must use the configured platform AR")

    def gcloud(*args, **kwargs):
        return run("gcloud", *args, env=env, **kwargs)

    def kubectl(*args, **kwargs):
        return run("kubectl", *args, env=env, **kwargs)

    chart = env["JUPYTER_CHART_URI"]
    version = env["JUPYTER_CHART_VERSION"]
    secret = settings.get("test_accounts_secret", "shared-test-accounts")
    accounts = json.loads(gcloud(
        "secrets", "versions", "access", "latest",
        f"--secret=shared-test-accounts-{group}", f"--project={project}", sensitive=True,
    ))
    approved = {member for task in settings["tasks"].values() for member in task["members"]}
    require(isinstance(accounts, dict) and all(
        isinstance(accounts.get(member), str) and PASSWORD_HASH.fullmatch(accounts[member])
        for member in approved
    ), "Secret Manager must contain valid hashes for all approved members")
    accounts = {member: accounts[member] for member in approved}

    gcloud("container", "clusters", "get-credentials", env["SHARED_GKE_CLUSTER"],
           f"--project={project}", f"--location={region}",
           "--dns-endpoint" if env.get("GKE_ENDPOINT_MODE") == "dns" else "--internal-ip")
    context = kubectl("config", "current-context").strip()
    namespaces = json.loads(kubectl("get", "namespaces", "-o", "json"))["items"]
    owners = {item["metadata"]["name"]: item["metadata"].get("labels", {}).get(OWNER_LABEL)
              for item in namespaces}
    targets = {group, *settings["tasks"]}
    require(all(owners[name] == group for name in targets & owners.keys()),
            "an existing namespace belongs to another deployment or lacks a group label")
    require(all(owner != group or name in targets for name, owner in owners.items()),
            "approved JSON must include every existing task in the group")

    for name, task in settings["tasks"].items():
        existing = kubectl("-n", name, "get", "deployment/notebook", "-o", "json",
                           "--ignore-not-found") if name in owners else ""
        if existing:
            spec = json.loads(existing)["spec"]
            old_members = [volume["secret"]["secretName"]
                           for volume in spec["template"]["spec"]["volumes"]
                           if volume["name"].startswith("member-")]
            new_members = [member_secret(member) for member in task["members"]]
            require(old_members == new_members or spec["replicas"] == 0,
                    f"{name}: stop the task and clear existing sessions before changing members")
        task_storage = task["storage"]
        if "storage_class" not in task_storage:
            kubectl("-n", name, "get", "pvc", task_storage["claim"])
        gsa = task["gsa"]
        gsa_project = gsa.split("@", 1)[1].removesuffix(".iam.gserviceaccount.com")
        gcloud("iam", "service-accounts", "describe", gsa, f"--project={gsa_project}")

    token = gcloud("auth", "print-access-token", sensitive=True).strip()
    run("helm", "registry", "login", registry.split("/", 1)[0], "--username",
        "oauth2accesstoken", "--password-stdin", env=env, input_text=token + "\n", sensitive=True)
    run("helm", "show", "chart", chart, "--version", version, env=env)

    namespace = {"apiVersion": "v1", "kind": "Namespace",
                 "metadata": {"name": group, "labels": {OWNER_LABEL: group}}}
    kubectl("apply", "-f", "-", input_text=json.dumps(namespace))
    account_secret = {"apiVersion": "v1", "kind": "Secret", "type": "Opaque",
                      "metadata": {"name": secret, "namespace": group},
                      "data": {"accounts.json": base64.b64encode(json.dumps(accounts).encode()).decode()}}
    kubectl("apply", "--server-side", "--field-manager=sandbox-test-accounts", "-f", "-",
            input_text=json.dumps(account_secret), sensitive=True)

    for name, task in settings["tasks"].items():
        gsa = task["gsa"]
        gsa_project = gsa.split("@", 1)[1].removesuffix(".iam.gserviceaccount.com")
        gcloud("iam", "service-accounts", "add-iam-policy-binding", gsa,
               f"--project={gsa_project}", "--role=roles/iam.workloadIdentityUser",
               f"--member=serviceAccount:{project}.svc.id.goog[{name}/ksa-jupyter-{name}]",
               "--condition=None", "--quiet")
        kubectl("apply", "-f", "-", input_text=json.dumps(task_resources(settings, name)))

    values = config_dir / "hub-values.json"
    values.write_text(json.dumps(group_values(settings)), encoding="utf-8")
    run("helm", "upgrade", "--install", "shared-hub", chart, "--version", version,
        "--namespace", group, "--values", str(values), "--atomic", "--timeout", "15m", env=env)
    for name in settings["tasks"]:
        deployment = json.loads(kubectl("-n", name, "get", "deployment/notebook", "-o", "json"))
        if deployment["spec"]["replicas"] > 0:
            kubectl("-n", name, "rollout", "status", "deployment/notebook", "--timeout=10m")

    reconcile_alb(settings, argparse.Namespace(
        context=context, project=project, region=region, url_map=env["SHARED_URL_MAP_NAME"],
    ))


def deploy(group, generation, expected_sha256, env, bucket, apply=reconcile):
    require(re.fullmatch(DNS, group), "invalid group")
    require(re.fullmatch(r"[0-9a-f]{64}", expected_sha256), "invalid group JSON SHA256")
    require(generation > 0, "invalid approved generation")
    lock = bucket.blob(f"shared-locks/{env['SHARED_URL_MAP_NAME']}.lock")
    # All groups share this URL map. Only the holder of this object generation can release it.
    deadline = time.monotonic() + 600
    while True:
        try:
            lock.upload_from_string(env["SHARED_BUILD_ID"], if_generation_match=0)
            break
        except PreconditionFailed:
            if time.monotonic() >= deadline:
                raise RuntimeError("Shared ALB deployment lock is busy; retry the approval later") from None
            time.sleep(15)
    lock_generation = lock.generation
    try:
        approved = bucket.get_blob(f"approved-groups/{group}/group.json")
        require(approved is not None and approved.generation == generation,
                "approval is missing or superseded by a newer group configuration")
        raw = bucket.blob(approved.name).download_as_bytes(if_generation_match=generation)
        require(hashlib.sha256(raw).hexdigest() == expected_sha256,
                "approved group JSON SHA256 mismatch")
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            config = directory / "group.json"
            config.write_bytes(raw)
            settings = load_group(config)
            require(settings["group"] == group, "approved JSON group does not match the object path")
            apply(settings, directory, env)
    finally:
        lock.delete(if_generation_match=lock_generation)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("group")
    parser.add_argument("generation", type=int)
    parser.add_argument("sha256")
    args = parser.parse_args()
    env = dict(os.environ)
    env["KUBECONFIG"] = "/workspace/shared-kubeconfig"
    os.environ["KUBECONFIG"] = env["KUBECONFIG"]
    deploy(args.group, args.generation, args.sha256, env,
           storage.Client().bucket(env["SHARED_REQUEST_BUCKET"]))
    print(f"[OK] Group {args.group}, approved generation {args.generation}")


if __name__ == "__main__":
    main()
