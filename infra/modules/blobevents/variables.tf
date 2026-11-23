variable "name" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "subscription_id" {
  description = "Azure subscription id, for built-in role definition ids"
  type        = string
}

variable "source_storage_account_id" {
  description = "The recordings account: its BlobCreated events are the topic's"
  type        = string
}

variable "incoming_container_name" {
  type = string
}

variable "manifest_name" {
  description = "The one blob name per meeting folder that starts a job (D15)"
  type        = string
}

variable "subscription_enabled" {
  description = "Create the manifest subscription. Event Grid validates the webhook on create, so the code must be deployed first (M7)."
  type        = bool
}

variable "webhook_url" {
  description = "The blobs extension's webhook with its system key; null while subscription_enabled is false"
  type        = string
  default     = null
  sensitive   = true
}

variable "max_delivery_attempts" {
  type = number
}

variable "deadletter_storage_account_id" {
  description = "Storage account that holds nothing but dead-letters: the topic identity gets its blob role on the whole account (Project 3 D24, D25)"
  type        = string
}

variable "deadletter_container_name" {
  type = string
}

variable "role_assignments_enabled" {
  type = bool
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
