variable "create_project" { type = bool }
variable "project_id" { type = string }
variable "project_name" { type = string }
variable "folder_id" {
  type    = string
  default = null
}
variable "billing_account" {
  type    = string
  default = null
}
variable "task_name" { type = string }
variable "expires_on" { type = string }
variable "region" { type = string }
variable "project_iam_service_account" { type = string }
variable "data_admin_service_account" { type = string }

variable "org_id" {
  type = string
  default = null
}
