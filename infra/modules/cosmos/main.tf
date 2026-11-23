# Cosmos DB for NoSQL, serverless: the job records (D17). Terraform owns the database and the container on Azure:
# data-plane RBAC can't create them, and the app never tries (scripts/init_stores.py is for the emulator only).
terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm" }
  }
}

resource "azurerm_cosmosdb_account" "this" {
  #checkov:skip=CKV_AZURE_99:No IP filter: the Flex app has no fixed egress IPs without VNet integration; Entra-only access (D39)
  #checkov:skip=CKV_AZURE_101:Public network access needed for the same reason (D39)
  #checkov:skip=CKV_AZURE_140:Checks the deprecated local_authentication_disabled; local_authentication_enabled = false below (Conftest enforces it)
  #checkov:skip=CKV_AZURE_100:CMK not used for a disposable lab account; Microsoft-managed keys
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  capabilities {
    name = "EnableServerless"
  }

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = var.location
    failover_priority = 0
  }

  local_authentication_enabled       = false # Entra ID + Cosmos data-plane RBAC only (D17)
  access_key_metadata_writes_enabled = false # no control-plane changes through account keys
  public_network_access_enabled      = true  # D39
  minimal_tls_version                = "Tls12"

  backup {
    type = "Continuous"
    tier = "Continuous7Days"
  }

  tags = var.tags
}

resource "azurerm_cosmosdb_sql_database" "this" {
  name                = var.database_name
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
}

# One record per meeting, id = meeting id: every access is a point read or write (D17).
resource "azurerm_cosmosdb_sql_container" "jobs" {
  name                = var.jobs_container_name
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
  database_name       = azurerm_cosmosdb_sql_database.this.name
  partition_key_paths = ["/id"]
}

resource "azurerm_monitor_diagnostic_setting" "account" {
  count                          = var.diagnostics_enabled ? 1 : 0
  name                           = "diag-to-law"
  target_resource_id             = azurerm_cosmosdb_account.this.id
  log_analytics_workspace_id     = var.log_analytics_workspace_id
  log_analytics_destination_type = "Dedicated" # resource-specific CDB* tables

  enabled_log {
    category_group = "allLogs"
  }
}
