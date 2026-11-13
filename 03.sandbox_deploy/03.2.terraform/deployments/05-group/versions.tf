terraform {
  required_version = ">= 1.5.7, < 2.0.0"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 7.0" }
  }
}
# Infrastructure Manager supplies tf-manager credentials. No user delegation.
provider "google" {
  project = var.identity_project_id
  scopes  = ["https://www.googleapis.com/auth/cloud-platform", "https://www.googleapis.com/auth/cloud-identity.groups"]
}
