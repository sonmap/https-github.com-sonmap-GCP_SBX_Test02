provider "google" {}

locals {
  project_roles = toset([
    "roles/bigquery.jobUser",
    "roles/browser",
  ])
}

resource "google_project_iam_member" "group" {
  for_each = local.project_roles
  project  = var.project_id
  role     = each.value
  member   = "group:${var.group_email}"
}
