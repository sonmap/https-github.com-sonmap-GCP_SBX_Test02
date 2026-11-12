variable "project_id" { type = string }
variable "region" { type = string }
variable "task_name" { type = string }
variable "group_email" { type = string }
variable "bigquery_dataset" { type = string }
variable "gcs_bucket" { type = string }
variable "gke_project_id" { type = string }
variable "gke_namespace" { type = string }
variable "jupyter_ksa_name" { type = string }

variable "jupyter_gsa_email" { type = string }
variable "identity_project_id" { type = string }

variable "create_jupyter_gsa" {
  type = bool
  default = false
}
variable "datalake_datasets" {
  type = list(object({ project_id = string, dataset_id = string }))
  default = []
}
