variable "name" {
  description = "Account name and custom subdomain (globally unique)"
  type        = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  description = "uaenorth has batch transcription and no fast transcription (D3)"
  type        = string
}

variable "allowed_fqdns" {
  description = "The only hosts the service itself may call: the recordings account's blob host (D41)"
  type        = list(string)
}

variable "diagnostics_enabled" {
  type = bool
}

variable "log_analytics_workspace_id" {
  type = string
}

variable "tags" {
  type = map(string)
}
