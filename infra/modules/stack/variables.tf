variable "name" {
  description = "Name stem, e.g. meet-local or meet-azure"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,13}$", var.name))
    error_message = "name: 3-14 chars, lowercase letters/digits/hyphens, starts with a letter."
  }
}

variable "location" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "storage_suffix" {
  description = "Storage DNS suffix of the cloud (public Azure); the recordings blob host is built from it (D41)"
  type        = string
  default     = "core.windows.net"
}

variable "log_analytics_workspace_id" {
  description = "Central workspace for diagnostics and Application Insights (log-slz-platform)"
  type        = string
}

variable "diagnostics_enabled" {
  description = "Diagnostic settings on every resource that has logs"
  type        = bool
  default     = true
}

variable "components" {
  description = "Everything is on by default. envs/local turns off what floci-az 0.16.0 can't create (D43)."
  type = object({
    cosmos       = optional(bool, true) # Microsoft.DocumentDB
    eventgrid    = optional(bool, true) # Microsoft.EventGrid system topic + subscription (+ the dead-letter account)
    function_app = optional(bool, true) # Microsoft.Web/serverfarms (FC1) + sites + Microsoft.Insights/components
    rbac         = optional(bool, true) # Microsoft.Authorization/roleAssignments + Cosmos sqlRoleAssignments
    openai       = optional(bool, true) # Microsoft.CognitiveServices OpenAI account + deployment
    speech       = optional(bool, true) # Microsoft.CognitiveServices SpeechServices account
  })
  default = {}
}

variable "blob_subscription_enabled" {
  description = "Create the manifest subscription. On Azure only after the code is deployed: Event Grid validates the webhook, and the blobs extension key exists only once the host has started (D40)."
  type        = bool
  default     = true
}

variable "trigger_function_name" {
  description = "The Blob-triggered function in src/function_app.py (the webhook's functionName)"
  type        = string
  default     = "meeting_job"
}

variable "event_max_delivery_attempts" {
  description = "Event Grid delivery attempts to the webhook = the local stub's maxDeliveryAttempts (D15)"
  type        = number
  default     = 5
}

variable "job_max_attempts" {
  description = "JOB_MAX_ATTEMPTS = host.json extensions.blobs.poisonBlobThreshold (D18)"
  type        = number
  default     = 5
}

variable "function_maximum_instance_count" {
  type    = number
  default = 2
}

variable "function_instance_memory_in_mb" {
  description = "2048 with Speech batch transcription; Whisper inside the Function would need 4096 (D19, decided in M7)"
  type        = number
  default     = 2048
}

variable "chat_deployment" {
  description = "Azure OpenAI chat deployment (D41). gpt-5.4-mini: GA, Global Standard in uaenorth, strict structured outputs (Project 3 D19)."
  type = object({
    model    = string
    version  = string
    sku      = string
    capacity = number
  })
  default = {
    model    = "gpt-5.4-mini"
    version  = "2026-03-17"
    sku      = "GlobalStandard"
    capacity = 50
  }
}

variable "chat_reasoning_effort" {
  description = "reasoning_effort for the chat model on Azure; a reasoning model gets max_completion_tokens, no temperature (D5)"
  type        = string
  default     = "low"
}

variable "summary_max_tokens" {
  description = "max_completion_tokens for a reasoning model: hidden reasoning tokens count against it"
  type        = number
  default     = 6000
}

variable "operator_object_id" {
  description = "Entra object id of the human operator: upload into incoming/ and read job records from the laptop (D42). Empty = none."
  type        = string
  default     = ""
}

variable "extra_app_settings" {
  description = "More app settings. Names/endpoints only, no secrets."
  type        = map(string)
  default     = {}
}
