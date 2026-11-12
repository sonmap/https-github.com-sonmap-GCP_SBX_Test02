variable "network_required" { type = bool }
variable "create_subnet" {
  type    = bool
  default = true
}
variable "host_project_id" { type = string }
variable "service_project_id" { type = string }
variable "network_name" { type = string }
variable "region" { type = string }
variable "subnet_name" {
  type    = string
  default = ""
}
variable "subnet_cidr" {
  type    = string
  default = ""
}
variable "private_google_access" {
  type    = bool
  default = true
}
variable "shared_vpc_join" {
  type    = bool
  default = false
}
