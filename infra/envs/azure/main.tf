variable "subscription_id" {
  description = "Lab subscription (set in gitignored terraform.tfvars)"
  type        = string
}

variable "location" {
  description = "Must offer Flex Consumption, Speech batch transcription and gpt-5.4-mini Global Standard (D3, D41)"
  type        = string
  default     = "uaenorth"
}

variable "blob_subscription_enabled" {
  description = "false until the code is deployed (M7): Event Grid validates the webhook, and the blobs extension key exists only once the host runs (D40)"
  type        = bool
  default     = false
}

variable "operator_object_id" {
  description = "Your Entra object id (az ad signed-in-user show --query id -o tsv); empty = no operator data roles (D42)"
  type        = string
  default     = ""
}

module "stack" {
  source   = "../../modules/stack"
  name     = "meet-azure"
  location = var.location

  # Project 1 platform workspace. ID built from names: the data source would list its shared keys.
  log_analytics_workspace_id = "/subscriptions/${var.subscription_id}/resourceGroups/rg-slz-platform/providers/Microsoft.OperationalInsights/workspaces/log-slz-platform"

  # components: all on (defaults). Real Azure gets the full stack.
  blob_subscription_enabled = var.blob_subscription_enabled
  operator_object_id        = var.operator_object_id

  tags = {
    project    = "meeting-summarizer"
    managed_by = "terraform"
    env        = "azure-lab"
  }
}

output "summary" {
  value = module.stack
}
