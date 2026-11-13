provider "google" {}

resource "google_project" "sandbox" {
  count = var.create_project ? 1 : 0

  project_id      = var.project_id
  name            = var.project_name
  folder_id       = var.folder_id
  org_id          = var.org_id
  auto_create_network = false
  billing_account = var.billing_account
  deletion_policy = "PREVENT"

  lifecycle {
    precondition {
      condition = (var.folder_id != null) != (var.org_id != null)
      error_message = "Specify exactly one of folder_id or org_id."
    }
  }

  labels = {
    environment = "sandbox"
    task        = var.task_name
    expires-on  = replace(var.expires_on, "-", "")
    managed-by  = "infrastructure-manager"
  }
}

# Reads either the newly created project or the approved existing project.
data "google_project" "sandbox" {
  project_id = var.project_id

  depends_on = [google_project.sandbox]
}

locals {
  required_services = toset([
    "bigquery.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "compute.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "serviceusage.googleapis.com",
    "storage.googleapis.com",
  ])
}

resource "google_project_service" "required" {
  for_each           = local.required_services
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false

  depends_on = [google_project.sandbox]
}

locals {
  bootstrap_roles = {
    project_iam_admin = {
      member = "serviceAccount:${var.project_iam_service_account}"
      role   = "roles/resourcemanager.projectIamAdmin"
    }
    data_bigquery_admin = {
      member = "serviceAccount:${var.data_admin_service_account}"
      role   = "roles/bigquery.admin"
    }
    data_storage_admin = {
      member = "serviceAccount:${var.data_admin_service_account}"
      role   = "roles/storage.admin"
    }
    data_sa_admin = {
      member = "serviceAccount:${var.data_admin_service_account}"
      role   = "roles/iam.serviceAccountAdmin"
    }
    data_service_usage = {
      member = "serviceAccount:${var.data_admin_service_account}"
      role   = "roles/serviceusage.serviceUsageConsumer"
    }
  }
}

resource "google_project_iam_member" "bootstrap" {
  for_each = local.bootstrap_roles
  project  = var.project_id
  role     = each.value.role
  member   = each.value.member

  depends_on = [google_project.sandbox]
}

output "project_id" {
  value = data.google_project.sandbox.project_id
}

output "project_number" {
  value = data.google_project.sandbox.number
}
