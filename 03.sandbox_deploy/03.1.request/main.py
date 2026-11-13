import hashlib
import hmac
import ipaddress
import io
import json
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

from flask import Flask, jsonify, request
from google.api_core.client_options import ClientOptions
from google.api_core.exceptions import PreconditionFailed
from google.cloud import storage
from google.cloud.devtools import cloudbuild_v1
from jsonschema import Draft202012Validator, FormatChecker

app = Flask(__name__)
REQUEST_RE = re.compile(r"^REQ-[A-Z0-9-]{6,64}$")
SCHEMA = json.loads(Path(__file__).with_name("sandbox-request.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())

STAGES = {
    "05-group": "group.zip",
    "10-project": "project.zip",
    "20-network": "network.zip",
    "30-project-iam": "project-iam.zip",
    "40-data": "data.zip",
}


def parse_gs_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("gs://"):
        raise ValueError("approved_json_uri must use gs://")
    bucket, separator, name = uri[5:].partition("/")
    if not bucket or not separator or not name:
        raise ValueError("approved_json_uri must include bucket and object")
    return bucket, name


def download_approved_request(uri: str, generation: int, expected_sha256: str) -> tuple[dict, bytes]:
    bucket_name, object_name = parse_gs_uri(uri)
    if bucket_name != os.environ["REQUEST_BUCKET"]:
        raise ValueError("request bucket is not allowed")

    blob = storage.Client().bucket(bucket_name).blob(object_name, generation=generation)
    raw = blob.download_as_bytes()
    actual_hash = hashlib.sha256(raw).hexdigest()
    if not hmac.compare_digest(actual_hash, expected_sha256.lower()):
        raise ValueError("request sha256 mismatch")

    payload = json.loads(raw)
    errors = sorted(VALIDATOR.iter_errors(payload), key=lambda error: list(error.path))
    if errors:
        location = ".".join(str(value) for value in errors[0].path) or "$"
        raise ValueError(f"request schema validation failed at {location}: {errors[0].message}")
    validate_semantics(payload)
    return payload, raw


def validate_semantics(payload: dict) -> None:
    customer_id = os.environ.get("CLOUD_IDENTITY_CUSTOMER_ID", "")
    if not re.fullmatch(r"C[A-Za-z0-9]+", customer_id):
        raise ValueError("configure CLOUD_IDENTITY_CUSTOMER_ID before deployment")
    identity = payload["identity"]
    group_name = identity.get("group_resource_name")
    membership_names = identity.get("membership_resource_names", {})
    if membership_names and not group_name:
        raise ValueError("group_resource_name is required when importing memberships")
    if not set(membership_names).issubset(identity["members"]):
        raise ValueError("imported membership keys must be approved identity.members")
    for name in membership_names.values():
        if not name.startswith(f"{group_name}/memberships/"):
            raise ValueError("membership resource must belong to group_resource_name")
    task = payload["task"]["name"]
    if payload["source"]["sha256"] == "0" * 64:
        raise ValueError("publish a new GCP_SBX_Test01 release and update request source first")
    if payload["identity"]["group_email"] != f"pgrp-gcp-dev-{task}@sonmap.net":
        raise ValueError("group_email must match the approved task name")
    if payload["gke"]["namespace"] != task:
        raise ValueError("GKE namespace must match the approved task name")

    if identity.get("create_jupyter_gsa", False) and len(task) > 18:
        raise ValueError("dedicated GSA task name must be at most 18 characters")
    if payload["project"]["create_project"] and not identity.get("create_jupyter_gsa", False):
        raise ValueError("new projects require identity.create_jupyter_gsa=true")
    if payload["data"].get("datalake_datasets") and not identity.get("create_jupyter_gsa", False):
        raise ValueError("datalake access requires a dedicated task GSA")

    network = payload["network"]
    if network["required"]:
        if network.get("create_subnet", True) or network["shared_vpc_join"]:
            raise ValueError("Host network changes are managed by VPC Admin; use an existing subnet with create_subnet=false and shared_vpc_join=false")
        if network.get("subnet_name") != f"subnet-{task}-an3":
            raise ValueError("subnet_name must match the approved task name")
        try:
            subnet = ipaddress.ip_network(network.get("subnet_cidr", ""), strict=True)
        except ValueError as error:
            raise ValueError("subnet_cidr must be a valid network address") from error
        if subnet.version != 4 or subnet.prefixlen != 24:
            raise ValueError("approved sandbox subnet must be IPv4 /24")
    elif network["shared_vpc_join"]:
        raise ValueError("shared_vpc_join cannot be true when network.required is false")


def download_source_archive(source: dict, destination: Path) -> Path:
    bucket_name, object_name = parse_gs_uri(source["archive_uri"])
    if bucket_name != os.environ["BUNDLE_BUCKET"]:
        raise ValueError("source archive must use the internal bundle bucket")
    if not object_name.startswith("platform-releases/"):
        raise ValueError("source archive must use platform-releases/")
    blob = storage.Client().bucket(bucket_name).blob(
        object_name, generation=int(source["generation"])
    )
    raw = blob.download_as_bytes()
    actual_hash = hashlib.sha256(raw).hexdigest()
    if not hmac.compare_digest(actual_hash, source["sha256"].lower()):
        raise ValueError("source archive sha256 mismatch")

    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        base = destination.resolve()
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if base not in target.parents and target != base:
                raise ValueError("unsafe source archive path")
        archive.extractall(destination)
    return destination


def stage_variables(payload: dict) -> dict[str, dict]:
    task = payload["task"]
    project = payload["project"]
    network = payload["network"]
    data = payload["data"]
    gke = payload["gke"]
    task_name = task["name"]
    jupyter_ksa = f"ksa-jupyter-{task_name}"
    create_gsa = payload["identity"].get("create_jupyter_gsa", False)
    identity_project = project["project_id"] if create_gsa else os.environ["SBX_GKE_PROJECT"]
    jupyter_gsa = (f"gsa-jupyter-{task_name}@{identity_project}.iam.gserviceaccount.com"
                   if create_gsa else f"sbx-manager@{identity_project}.iam.gserviceaccount.com")
    sandbox_project = os.environ["SBX_GKE_PROJECT"]

    return {
        "05-group": {
            "identity_project_id": sandbox_project,
            "customer_id": os.environ["CLOUD_IDENTITY_CUSTOMER_ID"],
            "group_email": payload["identity"]["group_email"],
            "display_name": task["display_name"],
            "members": payload["identity"]["members"],
        },
        "10-project": {
            "create_project": project["create_project"],
            "project_id": project["project_id"], "project_name": project["project_name"],
            "folder_id": project.get("folder_id"), "org_id": project.get("org_id"),
            "billing_account": project.get("billing_account"),
            "task_name": task_name, "expires_on": task["expires_on"], "region": network["region"],
            "project_iam_service_account": f"tf-manager@{sandbox_project}.iam.gserviceaccount.com",
            "data_admin_service_account": f"tf-manager@{sandbox_project}.iam.gserviceaccount.com",
        },
        "20-network": {
            "network_required": network["required"], "create_subnet": network.get("create_subnet", True),
            "host_project_id": network["host_project_id"],
            "service_project_id": project["project_id"], "network_name": network["network_name"],
            "region": network["region"], "subnet_name": network.get("subnet_name") or "",
            "subnet_cidr": network.get("subnet_cidr") or "",
            "private_google_access": network.get("private_google_access", True),
            "shared_vpc_join": network["shared_vpc_join"],
        },
        "30-project-iam": {
            "project_id": project["project_id"], "group_email": payload["identity"]["group_email"],
        },
        "40-data": {
            "project_id": project["project_id"], "region": network["region"], "task_name": task_name,
            "group_email": payload["identity"]["group_email"],
            "bigquery_dataset": data["bigquery_dataset"], "gcs_bucket": data["gcs_bucket"],
            "gke_project_id": gke["project_id"], "gke_namespace": gke["namespace"],
            "jupyter_ksa_name": jupyter_ksa,
            "jupyter_gsa_email": jupyter_gsa,
            "identity_project_id": identity_project,
            "create_jupyter_gsa": create_gsa,
            "datalake_datasets": data.get("datalake_datasets", []),
        },
    }


def zip_directory(source: Path) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source))
    return output.getvalue()


def write_static_data_imports(work: Path, payload: dict) -> None:
    """Write literal import IDs for data resources that were approved for adoption.

    Infrastructure Manager uses Terraform 1.5.7, where import block IDs cannot
    reference input variables. This generated file is included only in the
    request-specific bundle, so its values are already approved and immutable.
    """
    if not payload["data"].get("adopt_existing_resources", False):
        return

    project_id = payload["project"]["project_id"]
    dataset_id = payload["data"]["bigquery_dataset"]
    bucket_name = payload["data"]["gcs_bucket"]
    imports = (
        "import {\n"
        "  to = google_bigquery_dataset.sandbox\n"
        f"  id = {json.dumps(f'projects/{project_id}/datasets/{dataset_id}')}\n"
        "}\n\n"
        "import {\n"
        "  to = google_storage_bucket.sandbox\n"
        f"  id = {json.dumps(bucket_name)}\n"
        "}\n"
    )
    (work / "imports.tf").write_text(imports, encoding="utf-8")


def write_static_group_imports(work: Path, payload: dict) -> None:
    """Import approved existing group/memberships with Terraform 1.5 literal IDs."""
    identity = payload["identity"]
    group_name = identity.get("group_resource_name")
    if not group_name:
        return
    blocks = [
        'import {\n  to = google_cloud_identity_group.sandbox\n'
        f'  id = {json.dumps(group_name)}\n}}\n'
    ]
    for email, name in sorted(identity.get("membership_resource_names", {}).items()):
        blocks.append(
            'import {\n'
            f'  to = google_cloud_identity_group_membership.member[{json.dumps(email)}]\n'
            f'  id = {json.dumps(name)}\n}}\n'
        )
    (work / "imports.tf").write_text("\n".join(blocks), encoding="utf-8")


def upload_immutable(blob, content: bytes, content_type: str) -> None:
    try:
        blob.upload_from_string(content, content_type=content_type, if_generation_match=0)
    except PreconditionFailed:
        # A repeated call for the same approved request and immutable release
        # reuses the already-created bundle.
        return


def assemble_bundles(payload: dict, raw_request: bytes) -> tuple[str, dict]:
    request_id = payload["request_id"]
    release_id = payload["source"]["release_id"]
    prefix = f"requests/{request_id}/{release_id}"
    bucket = storage.Client().bucket(os.environ["BUNDLE_BUCKET"])
    variables = stage_variables(payload)
    manifest = {"request_id": request_id, "release_id": release_id, "bundles": {}}

    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        source_root = download_source_archive(payload["source"], temp / "source")
        deployment_root = source_root / "08.sandbox_setup_02_terraform" / "deployments"
        for stage, archive_name in STAGES.items():
            source = deployment_root / stage
            if not source.is_dir():
                raise ValueError(f"missing Terraform root module: {stage}")
            if payload["identity"].get("create_jupyter_gsa", False):
                if stage == "40-data" and 'resource "google_service_account" "jupyter"' not in (source / "main.tf").read_text():
                    raise ValueError("source release does not support dedicated task GSA; publish a new release")
                if stage == "10-project" and payload["project"].get("org_id") and 'variable "org_id"' not in (source / "variables.tf").read_text():
                    raise ValueError("source release does not support org_id; publish a new release")
            work = temp / "work" / stage
            shutil.copytree(source, work)
            if stage == "05-group":
                write_static_group_imports(work, payload)
            if stage == "40-data":
                write_static_data_imports(work, payload)
            (work / "terraform.auto.tfvars.json").write_text(
                json.dumps(variables[stage], indent=2, sort_keys=True), encoding="utf-8"
            )
            archive = zip_directory(work)
            object_name = f"{prefix}/{archive_name}"
            upload_immutable(bucket.blob(object_name), archive, "application/zip")
            manifest["bundles"][stage] = {
                "uri": f"gs://{bucket.name}/{object_name}",
                "sha256": hashlib.sha256(archive).hexdigest(),
            }

        upload_immutable(bucket.blob(f"{prefix}/approved-request.json"), raw_request, "application/json")
        upload_immutable(
            bucket.blob(f"{prefix}/manifest.json"),
            json.dumps(manifest, indent=2, sort_keys=True).encode(),
            "application/json",
        )
    return f"gs://{bucket.name}/{prefix}", manifest


def start_build(payload: dict, request_uri: str, bundle_prefix: str):
    project = os.environ["SBX_GKE_PROJECT"]
    region = os.environ["GCP_REGION"]
    task = payload["task"]["name"]
    request_id = payload["request_id"]
    release_id = payload["source"]["release_id"]
    deployment_key = hashlib.sha256(payload["project"]["project_id"].encode()).hexdigest()[:8]
    worker_pool = os.environ["WORKER_POOL"]
    service_account = f"projects/{project}/serviceAccounts/tf-manager@{project}.iam.gserviceaccount.com"

    # Infrastructure Manager manages Google Cloud resources only. Kubernetes
    # objects are applied by a separate Cloud Build running in the private pool.
    stages = [
        ("group", "group.zip", "tf-manager"),
        ("project", "project.zip", "tf-manager"),
    ]
    if payload["network"]["required"]:
        stages.append(("network", "network.zip", "tf-manager"))
    stages.extend([
        ("project-iam", "project-iam.zip", "tf-manager"),
        ("data", "data.zip", "tf-manager"),
    ])

    commands = ["set -euo pipefail"]
    for name, archive, account_id in stages:
        account_email = f"{account_id}@{project}.iam.gserviceaccount.com"
        commands.append(
            "gcloud infra-manager deployments apply "
            f"\"projects/{project}/locations/{region}/deployments/sbxtest01-{task}-{deployment_key}-{name}\" "
            f"--service-account=\"projects/{project}/serviceAccounts/{account_email}\" "
            f"--gcs-source=\"{bundle_prefix}/{archive}\" "
            f"--worker-pool=\"{worker_pool}\" "
            "--provider-source=SERVICE_MAINTAINED "
            f"--annotations=\"request_id={request_id},task={task}\" "
            "--quiet"
        )
        if name == "group":
            # Group IAM visibility may lag creation. Failures stop the build.
            commands.append("sleep 60")

    # The approved source release and runner image use the same immutable tag.
    # This prevents a newer :latest image from changing an already-approved build.
    automation_image = (
        f"{region}-docker.pkg.dev/{project}/ar-sbxtest01-platform/"
        f"sbxtest01-automation-runner:{release_id}"
    )
    common_env = [
        f"SBX_GKE_PROJECT={project}",
        f"GCP_REGION={region}",
        f"GKE_ADMIN_SA=tf-manager@{project}.iam.gserviceaccount.com",
        f"LB_ADMIN_SA=tf-manager@{project}.iam.gserviceaccount.com",
        f"JUPYTER_CHART_URI={os.environ['JUPYTER_CHART_URI']}",
        f"JUPYTER_CHART_VERSION={os.environ['JUPYTER_CHART_VERSION']}",
        f"WORKER_POOL={worker_pool}",
        "SHARED_URL_MAP_NAME=urlmap-alb-sbxtest01-shared",
        "KUBECONFIG=/workspace/kubeconfig",
        f"GKE_ENDPOINT_MODE={os.environ.get('GKE_ENDPOINT_MODE', 'internal')}",
    ]
    child_build = {
        "steps": [
            {
                "name": automation_image,
                "entrypoint": "python3",
                "args": [
                    "/opt/sandbox/apply_gke_workload.py",
                    f"{bundle_prefix}/approved-request.json",
                ],
                "env": common_env,
            },
            {
                "name": automation_image,
                "entrypoint": "python3",
                "args": [
                    "/opt/sandbox/reconcile_postdeploy.py",
                    "/workspace/approved-request.json",
                ],
                "env": common_env,
            },
        ],
        "options": {
            "logging": "CLOUD_LOGGING_ONLY",
            "pool": {"name": worker_pool},
        },
        "serviceAccount": service_account,
        "timeout": "3600s",
    }
    child_config = json.dumps(child_build)
    gke_command = (
        "set -euo pipefail\n"
        "cat > /workspace/gke-build.json <<'JSON'\n"
        f"{child_config}\n"
        "JSON\n"
        f"gcloud builds submit --no-source "
        f"--config=/workspace/gke-build.json --project={project} "
        f"--region={region} --quiet"
    )

    build_spec = {
        "steps": [
            {
                "name": "gcr.io/google.com/cloudsdktool/cloud-sdk:slim",
                "entrypoint": "bash",
                "args": ["-ceu", "\n".join(commands)],
            },
            {
                "name": "gcr.io/google.com/cloudsdktool/cloud-sdk:slim",
                "entrypoint": "bash",
                "args": ["-ceu", gke_command],
            },
        ],
        "options": {"logging": "CLOUD_LOGGING_ONLY", "pool": {"name": worker_pool}},
        "service_account": service_account,
        "timeout": "14400s",
    }
    build = cloudbuild_v1.Build(build_spec)
    client = cloudbuild_v1.CloudBuildClient(
        client_options=ClientOptions(
            api_endpoint=f"{region}-cloudbuild.googleapis.com"
        )
    )
    return client.create_build(request=cloudbuild_v1.CreateBuildRequest(
        parent=f"projects/{project}/locations/{region}",
        project_id=project,
        build=build,
    ))


def start_build_once(payload: dict, request_uri: str, bundle_prefix: str) -> tuple[str, bool]:
    bucket_name, prefix = parse_gs_uri(bundle_prefix)
    lock = storage.Client().bucket(bucket_name).blob(f"{prefix}/dispatch.json")
    starting = json.dumps({"request_id": payload["request_id"], "status": "STARTING"}).encode()
    try:
        lock.upload_from_string(starting, content_type="application/json", if_generation_match=0)
    except PreconditionFailed:
        previous = json.loads(lock.download_as_bytes())
        operation = previous.get("operation")
        if operation:
            return operation, True
        raise ValueError("this approved request is already being dispatched")

    lock.reload()
    generation = lock.generation
    try:
        operation = start_build(payload, request_uri, bundle_prefix).operation.name
        dispatched = json.dumps({
            "request_id": payload["request_id"], "status": "DISPATCHED", "operation": operation,
        }).encode()
        lock.upload_from_string(
            dispatched, content_type="application/json", if_generation_match=generation
        )
        return operation, False
    except Exception:
        lock.delete(if_generation_match=generation)
        raise


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/provision")
def provision():
    body = request.get_json(silent=True) or {}
    request_id = body.get("request_id", "")
    if not REQUEST_RE.fullmatch(request_id):
        return jsonify(error="invalid request_id"), 400
    try:
        request_uri = body["approved_json_uri"]
        _, request_object = parse_gs_uri(request_uri)
        if request_object != f"approved/{request_id}/request.json":
            raise ValueError("approved_json_uri must use approved/<request_id>/request.json")
        payload, raw = download_approved_request(request_uri, int(body["generation"]), body["sha256"])
        if payload["request_id"] != request_id:
            raise ValueError("request_id does not match approved JSON")
        bundle_prefix, manifest = assemble_bundles(payload, raw)
        operation, duplicate = start_build_once(payload, request_uri, bundle_prefix)
    except (KeyError, TypeError, ValueError) as error:
        return jsonify(error=str(error), request_id=request_id), 400
    except Exception:
        app.logger.exception("provisioning request failed")
        return jsonify(error="internal provisioning error", request_id=request_id), 500
    return jsonify(
        request_id=request_id, status="ACCEPTED", bundle_prefix=bundle_prefix,
        operation=operation, duplicate=duplicate, bundle_count=len(manifest["bundles"]),
    ), 202
