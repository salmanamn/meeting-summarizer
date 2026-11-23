# Every data-plane permission in the stack, each at the narrowest scope that works (D42).
# Built-in roles by id, not name (no lookup at apply). Nothing at resource-group or subscription scope.
locals {
  role_ids = {
    storage_blob_data_owner       = "b7e6dc6d-f1e8-4753-8033-0f276bb0955b"
    storage_blob_data_contributor = "ba92f5b4-2d11-453d-a403-e96b0029c9fe"
    storage_blob_data_reader      = "2a2b9908-6ea1-4ae2-8e65-a410df84e7d1"
    storage_queue_data_contrib    = "974c5e8b-45b9-4653-ba55-5f855dd0fb88"
    monitoring_metrics_publisher  = "3913510d-42f4-4e42-8a64-420c390055eb"
    cognitive_openai_user         = "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd"
    cognitive_speech_user         = "f2dc8367-1007-4938-bd23-fe263f013447"
  }

  # The app identity (the Function).
  app_roles = merge(
    var.components.function_app ? {
      # Host storage: the deployment package, host leases, and the queue the Event Grid Blob trigger runs from
      host_blob  = { scope = module.storage.account_id, role = "storage_blob_data_owner" }
      host_queue = { scope = module.storage.account_id, role = "storage_queue_data_contrib" }
      # The trigger's connection (RecordingsStorage): read incoming/, write transcripts/, and the poison queue the
      # Blob trigger writes in the same account
      recordings_blob  = { scope = module.recordings.account_id, role = "storage_blob_data_owner" }
      recordings_queue = { scope = module.recordings.account_id, role = "storage_queue_data_contrib" }
      # Telemetry ingestion with local auth disabled
      appinsights = { scope = azurerm_application_insights.this[0].id, role = "monitoring_metrics_publisher" }
    } : {},
    var.components.openai ? {
      openai_user = { scope = module.openai[0].account_id, role = "cognitive_openai_user" }
    } : {},
    var.components.speech ? {
      # Submit, poll, read and delete batch transcriptions with an Entra token (M6)
      speech_user = { scope = module.speech[0].account_id, role = "cognitive_speech_user" }
    } : {},
  )

  # The human operator (D42): upload meetings into incoming/ and read job records from the laptop (M7). Nothing
  # else; omitted when operator_object_id is empty.
  operator_enabled = var.components.rbac && length(var.operator_object_id) > 0
}

resource "azurerm_role_assignment" "app" {
  for_each           = var.components.rbac ? local.app_roles : {}
  scope              = each.value.scope
  role_definition_id = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/providers/Microsoft.Authorization/roleDefinitions/${local.role_ids[each.value.role]}"
  principal_id       = azurerm_user_assigned_identity.app.principal_id
  principal_type     = "ServicePrincipal"
  description        = "meeting-summarizer app identity: ${each.key}"
}

# The Speech account's system identity reads the recordings for batch transcription, without SAS (D3): read only,
# on incoming/ only.
resource "azurerm_role_assignment" "speech_reads_incoming" {
  count              = var.components.rbac && var.components.speech ? 1 : 0
  scope              = module.recordings.container_ids[local.incoming_container]
  role_definition_id = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/providers/Microsoft.Authorization/roleDefinitions/${local.role_ids.storage_blob_data_reader}"
  principal_id       = module.speech[0].principal_id
  principal_type     = "ServicePrincipal"
  description        = "meeting-summarizer Speech account: read recordings for batch transcription"
}

# Cosmos data plane has its own RBAC. Built-in Data Contributor, scoped to the meetings database only.
resource "azurerm_cosmosdb_sql_role_assignment" "app" {
  count               = var.components.rbac && var.components.cosmos ? 1 : 0
  resource_group_name = azurerm_resource_group.this.name
  account_name        = module.cosmos[0].account_name
  role_definition_id  = "${module.cosmos[0].account_id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id        = azurerm_user_assigned_identity.app.principal_id
  scope               = "${module.cosmos[0].account_id}/dbs/${module.cosmos[0].database_name}"
}

resource "azurerm_role_assignment" "operator_upload" {
  count              = local.operator_enabled ? 1 : 0
  scope              = module.recordings.container_ids[local.incoming_container]
  role_definition_id = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/providers/Microsoft.Authorization/roleDefinitions/${local.role_ids.storage_blob_data_contributor}"
  principal_id       = var.operator_object_id
  principal_type     = "User"
  description        = "meeting-summarizer operator: upload meetings from the laptop"
}

# Built-in Data Reader: the operator reads job records, never writes them.
resource "azurerm_cosmosdb_sql_role_assignment" "operator" {
  count               = local.operator_enabled && var.components.cosmos ? 1 : 0
  resource_group_name = azurerm_resource_group.this.name
  account_name        = module.cosmos[0].account_name
  role_definition_id  = "${module.cosmos[0].account_id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000001"
  principal_id        = var.operator_object_id
  scope               = "${module.cosmos[0].account_id}/dbs/${module.cosmos[0].database_name}"

  depends_on = [azurerm_cosmosdb_sql_role_assignment.app] # Cosmos role assignments on one account: one at a time
}
