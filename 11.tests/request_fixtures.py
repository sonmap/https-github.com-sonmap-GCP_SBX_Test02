"""Synthetic request data for local tests, independent of deployment examples."""


def make_request(*, new_project=False):
    task = "sbx03" if new_project else "sbx01"
    project = f"gcp-sbx-edp-{task}" if new_project else "pjt-net-hub-base"
    request = {
        "schema_version": "1.0",
        "request_id": "REQ-LOCAL-TEST-001",
        "approval": {
            "status": "APPROVED",
            "approval_id": "test-approval",
            "approved_at": "2026-01-01T00:00:00Z",
        },
        "action": "CREATE",
        "task": {"name": task, "display_name": "Local test assignment", "expires_on": "2026-12-31"},
        "identity": {
            "group_email": f"pgrp-gcp-dev-{task}@sonmap.net",
            "members": ["tester01@sonmap.net", "tester02@sonmap.net"],
        },
        "project": {"create_project": new_project, "project_id": project, "project_name": "Local test sandbox"},
        "network": {
            "required": False,
            "create_subnet": False,
            "host_project_id": "gcp-prod-edp-hub-vpchost",
            "network_name": "vpc-prod-edp-hub",
            "region": "asia-northeast3",
            "shared_vpc_join": False,
        },
        "data": {
            "bigquery_dataset": f"{task}_main",
            "gcs_bucket": f"{project}-{task}-data",
            "adopt_existing_resources": not new_project,
        },
        "gke": {
            "project_id": "gcp-sbx-edp-gke01",
            "cluster_name": "gke-sbx-main-an3",
            "location": "asia-northeast3",
            "namespace": task,
            "jupyter_domain": f"jupyter-{task}.sonmap.net",
        },
        "source": {
            "release_id": "git-test123",
            "archive_uri": (
                "gs://gcp-sbx-edp-gke01-sbxtest01-bundles/"
                "platform-releases/git-test123/sandbox-source.zip"
            ),
            "generation": 1,
            "sha256": "a" * 64,
        },
    }
    if new_project:
        request["project"].update(org_id="123456789012", billing_account="000000-000000-000000")
        request["identity"]["create_jupyter_gsa"] = True
        request["data"]["datalake_datasets"] = [{"project_id": "pjt-c-admin", "dataset_id": "dlk_sample"}]
    return request
