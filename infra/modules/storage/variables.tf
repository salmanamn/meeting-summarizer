variable "name" {
  description = "Storage account name (3-24 lowercase letters and digits, globally unique)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{3,24}$", var.name))
    error_message = "name: 3-24 lowercase letters and digits."
  }
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "containers" {
  description = "Private blob containers to create in the account"
  type        = set(string)
}

variable "resource_instance_ids" {
  description = "Resource instances the account trusts by name (resource access rules); only the recordings account has one: the Speech account (D3)"
  type        = list(string)
  default     = []
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
