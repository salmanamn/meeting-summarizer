variable "full_stack" {
  description = <<-EOT
    false (default): only what floci-az 0.16.0 can create, for plan and apply.
    true: every component, for `plan` only (the CI policy gate). Never apply with true: floci-az 0.16.0 answers 404
    for Cosmos DB, App Service plans, App Insights and role assignments, and 200 where azurerm requires 201 for
    Event Grid (Project 3 D18, D43).
  EOT
  type        = bool
  default     = false
}

data "azurerm_client_config" "current" {}

module "stack" {
  source   = "../../modules/stack"
  name     = "meet-local"
  location = "eastus"

  # Same id shape as on Azure. floci-az can't create workspaces, but it stores diagnostic settings without
  # checking their destination, so the settings are still created locally.
  log_analytics_workspace_id = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/resourceGroups/rg-slz-platform/providers/Microsoft.OperationalInsights/workspaces/log-slz-platform"

  components = {
    cosmos       = var.full_stack
    eventgrid    = var.full_stack
    function_app = var.full_stack
    rbac         = var.full_stack
    openai       = var.full_stack
    speech       = var.full_stack
  }

  # The full plan includes the manifest subscription, so the gate checks it. Its webhook URL (host name and the
  # blobs extension key) is unknown until apply, so the plan needs nothing from the emulator for it.
  blob_subscription_enabled = true
  operator_object_id        = "00000000-0000-0000-0000-0000000000aa" # a placeholder: the operator's roles are planned and gated too

  tags = {
    project    = "meeting-summarizer"
    managed_by = "terraform"
    env        = "local"
  }
}

output "summary" {
  value = module.stack
}
