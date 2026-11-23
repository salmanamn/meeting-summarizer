# Azure AI Speech for batch transcription (D3, M6): one account, Entra ID only. Project 4's module (its D59) with
# two differences: the system-assigned identity is what reads the recordings (a user-assigned one isn't supported
# for this, D3), and outbound access is restricted to the recordings account's blob host instead of nothing (D41).
terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm" }
  }
}

resource "azurerm_cognitive_account" "this" {
  #checkov:skip=CKV_AZURE_134:Public endpoint: the Flex app has no VNet integration in the lab (D39); Entra-only access
  #checkov:skip=CKV2_AZURE_22:CMK not used for a disposable lab account; Microsoft-managed keys
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
  kind                = "SpeechServices"
  sku_name            = "S0" # pay per audio hour; F0 is one per subscription

  custom_subdomain_name = var.name # required for Entra ID tokens: https://<name>.cognitiveservices.azure.com/

  local_auth_enabled                 = false # no keys
  public_network_access_enabled      = true  # D39
  outbound_network_access_restricted = true
  fqdns                              = var.allowed_fqdns # the recordings account's blob host, and nothing else

  identity {
    type = "SystemAssigned" # reads incoming/ with Storage Blob Data Reader (rbac.tf); no SAS anywhere (D3)
  }

  tags = var.tags
}

resource "azurerm_monitor_diagnostic_setting" "account" {
  count                      = var.diagnostics_enabled ? 1 : 0
  name                       = "diag-to-law"
  target_resource_id         = azurerm_cognitive_account.this.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category_group = "allLogs"
  }
}
