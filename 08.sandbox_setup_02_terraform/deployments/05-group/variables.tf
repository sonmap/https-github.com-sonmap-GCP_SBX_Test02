variable "identity_project_id" { type = string }
variable "customer_id" {
  type = string
  validation {
    condition     = can(regex("^C[A-Za-z0-9]+$", var.customer_id))
    error_message = "Set the actual Cloud Identity customer ID, starting with C."
  }
}
variable "group_email" { type = string }
variable "display_name" { type = string }
variable "members" { type = set(string) }
