# The Blob trigger's events (D12, D15, D40): an Event Grid system topic on the recordings account, and one
# subscription that sends BlobCreated for incoming/<meeting-id>/meeting.json to the Functions blobs extension's
# webhook. The same filters, attempts and schema as the local stub (emulators/eventgrid/subscriptions.json); a unit
# test keeps the two equal. Undeliverable events go to a storage account of their own, written with the topic's
# system identity (Project 3 D24, D25).
terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm" }
  }
}

resource "azurerm_eventgrid_system_topic" "this" {
  name                   = var.name
  location               = var.location
  resource_group_name    = var.resource_group_name
  source_arm_resource_id = var.source_storage_account_id
  topic_type             = "Microsoft.Storage.StorageAccounts"

  identity {
    type = "SystemAssigned" # writes dead-letters to blob
  }

  tags = var.tags
}

# Event Grid validates this role on the storage account, not on the container (Project 3 D24). The account holds
# only the dead-letter container, so account scope is the narrowest scope that works.
resource "azurerm_role_assignment" "topic_deadletter" {
  count              = var.role_assignments_enabled ? 1 : 0
  scope              = var.deadletter_storage_account_id
  role_definition_id = "/subscriptions/${var.subscription_id}/providers/Microsoft.Authorization/roleDefinitions/ba92f5b4-2d11-453d-a403-e96b0029c9fe" # Storage Blob Data Contributor
  principal_id       = azurerm_eventgrid_system_topic.this.identity[0].principal_id
  principal_type     = "ServicePrincipal"
}

resource "azurerm_eventgrid_system_topic_event_subscription" "manifest" {
  count                 = var.subscription_enabled ? 1 : 0
  name                  = "meeting-manifest"
  system_topic          = azurerm_eventgrid_system_topic.this.name
  resource_group_name   = var.resource_group_name
  event_delivery_schema = "EventGridSchema" # what the blobs extension's webhook reads
  included_event_types  = ["Microsoft.Storage.BlobCreated"]

  # Only manifests reach the Function (D15): the trigger's path is not a filter in Event Grid mode.
  subject_filter {
    subject_begins_with = "/blobServices/default/containers/${var.incoming_container_name}/blobs/"
    subject_ends_with   = "/${var.manifest_name}"
    case_sensitive      = true
  }

  # https://<app>/runtime/webhooks/blobs?functionName=Host.Functions.<function>&code=<blobs_extension key>:
  # the only endpoint the Event Grid-based Blob trigger takes. The key makes the URL sensitive (D40).
  webhook_endpoint {
    url                               = var.webhook_url
    max_events_per_batch              = 1
    preferred_batch_size_in_kilobytes = 64
  }

  retry_policy {
    max_delivery_attempts = var.max_delivery_attempts # the stub's maxDeliveryAttempts
    event_time_to_live    = 1440                      # minutes
  }

  dead_letter_identity {
    type = "SystemAssigned"
  }

  storage_blob_dead_letter_destination {
    storage_account_id          = var.deadletter_storage_account_id
    storage_blob_container_name = var.deadletter_container_name
  }

  depends_on = [azurerm_role_assignment.topic_deadletter]
}

resource "azurerm_monitor_diagnostic_setting" "topic" {
  count                      = var.diagnostics_enabled ? 1 : 0
  name                       = "diag-to-law"
  target_resource_id         = azurerm_eventgrid_system_topic.this.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category_group = "allLogs"
  }
}
