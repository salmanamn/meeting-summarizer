# One hardened storage account with its private containers. Entra ID only: no account keys, no SAS, no anonymous
# blobs. The stack creates three (D38): the Function App's host storage (AzureWebJobsStorage + the Flex deployment
# package), the recordings account (incoming/ + transcripts/, the Blob trigger's source) and an account of its own
# for Event Grid dead-letters (Project 3 D25).
terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm" }
  }
}

resource "azurerm_storage_account" "this" {
  #checkov:skip=CKV_AZURE_206:LRS is intentional for a disposable lab stack (destroyed every session)
  #checkov:skip=CKV_AZURE_59:The Flex app (no VNet integration) and the laptop reach it over the public endpoint; access is Entra-only (D39)
  #checkov:skip=CKV_AZURE_35:Same as CKV_AZURE_59: default action Deny needs VNet integration of the Flex app (Project 7, D39)
  #checkov:skip=CKV2_AZURE_33:Private endpoints need VNet integration of the Flex app; deferred (D39)
  #checkov:skip=CKV2_AZURE_1:CMK not used for a disposable lab account; Microsoft-managed keys + infrastructure encryption
  #checkov:skip=CKV_AZURE_33:Classic queue logging is legacy; blob resource logs go to log-slz-platform via diagnostic settings
  #checkov:skip=CKV2_AZURE_41:No SAS is ever issued (shared key disabled); the SAS policy below is belt and braces
  name                     = var.name
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_kind             = "StorageV2"
  account_tier             = "Standard"
  account_replication_type = "LRS"

  https_traffic_only_enabled = true
  min_tls_version            = "TLS1_2"

  allow_nested_items_to_be_public = false
  public_network_access_enabled   = true # no VNet in the lab (D39)

  shared_access_key_enabled        = false
  default_to_oauth_authentication  = true
  local_user_enabled               = false
  cross_tenant_replication_enabled = false

  infrastructure_encryption_enabled = true

  # Default Allow while the Flex app has no VNet integration (D39). No blanket trusted-services exception; the
  # recordings account names its one trusted resource instance, the stack's Speech account (D3), so a later
  # default Deny changes one value and nothing else.
  network_rules {
    default_action = "Allow"
    bypass         = ["None"]

    dynamic "private_link_access" {
      for_each = var.resource_instance_ids
      content {
        endpoint_resource_id = private_link_access.value
      }
    }
  }

  blob_properties {
    delete_retention_policy {
      days = 7
    }
    container_delete_retention_policy {
      days = 7
    }
  }

  sas_policy {
    expiration_period = "00.04:00:00"
    expiration_action = "Log"
  }

  tags = var.tags

  lifecycle {
    # floci-az doesn't store it; set-at-creation on Azure anyway
    ignore_changes = [infrastructure_encryption_enabled]
  }
}

resource "azurerm_storage_container" "this" {
  #checkov:skip=CKV2_AZURE_21:Blob read logging is enabled on the blob service via the diagnostic setting below
  for_each              = var.containers
  name                  = each.value
  storage_account_id    = azurerm_storage_account.this.id
  container_access_type = "private"
}

resource "azurerm_monitor_diagnostic_setting" "blob" {
  count                      = var.diagnostics_enabled ? 1 : 0
  name                       = "diag-to-law"
  target_resource_id         = "${azurerm_storage_account.this.id}/blobServices/default"
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category_group = "allLogs"
  }
}
