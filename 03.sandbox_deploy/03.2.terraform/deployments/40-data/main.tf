provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_service_account" "jupyter" {
  count        = var.create_jupyter_gsa ? 1 : 0
  project      = var.project_id
  account_id   = "gsa-jupyter-${var.task_name}"
  display_name = "Jupyter ${var.task_name}"
}

data "google_service_account" "jupyter" {
  count      = var.create_jupyter_gsa ? 0 : 1
  project    = var.identity_project_id
  account_id = var.jupyter_gsa_email
}

locals {
  jupyter_email = var.create_jupyter_gsa ? google_service_account.jupyter[0].email : data.google_service_account.jupyter[0].email
  jupyter_name  = var.create_jupyter_gsa ? google_service_account.jupyter[0].name : data.google_service_account.jupyter[0].name
}

resource "google_bigquery_dataset" "sandbox" {
  project                    = var.project_id
  dataset_id                 = var.bigquery_dataset
  location                   = var.region
  delete_contents_on_destroy = false

  labels = {
    task       = var.task_name
    managed-by = "infrastructure-manager"
  }
}

resource "google_bigquery_dataset_iam_member" "group" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.sandbox.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "group:${var.group_email}"
}

resource "google_bigquery_dataset_iam_member" "jupyter" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.sandbox.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${local.jupyter_email}"
}

resource "google_project_iam_member" "jupyter_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${local.jupyter_email}"
}

resource "google_storage_bucket" "sandbox" {
  project                     = var.project_id
  name                        = var.gcs_bucket
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  versioning {
    enabled = true
  }

  labels = {
    task       = var.task_name
    managed-by = "infrastructure-manager"
  }
}

resource "google_storage_bucket_iam_member" "group" {
  bucket = google_storage_bucket.sandbox.name
  role   = "roles/storage.objectUser"
  member = "group:${var.group_email}"
}

resource "google_storage_bucket_iam_member" "jupyter" {
  bucket = google_storage_bucket.sandbox.name
  role   = "roles/storage.objectUser"
  member = "serviceAccount:${local.jupyter_email}"
}

resource "google_service_account_iam_member" "workload_identity" {
  service_account_id = local.jupyter_name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.gke_project_id}.svc.id.goog[${var.gke_namespace}/${var.jupyter_ksa_name}]"
}

output "jupyter_service_account" { value = local.jupyter_email }
output "dataset_id" { value = google_bigquery_dataset.sandbox.dataset_id }
output "bucket_name" { value = google_storage_bucket.sandbox.name }

# Additive IAM grants on explicitly approved existing datalake datasets.
resource "google_bigquery_dataset_iam_member" "datalake_reader" {
  for_each = { for item in var.datalake_datasets : "${item.project_id}/${item.dataset_id}" => item }
  project    = each.value.project_id
  dataset_id = each.value.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${local.jupyter_email}"
}
