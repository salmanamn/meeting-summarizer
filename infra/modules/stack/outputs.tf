output "resource_group_name" {
  value = azurerm_resource_group.this.name
}

output "app_identity" {
  value = {
    id           = azurerm_user_assigned_identity.app.id
    client_id    = azurerm_user_assigned_identity.app.client_id
    principal_id = azurerm_user_assigned_identity.app.principal_id
  }
}

output "storage_account_name" {
  value = module.storage.account_name
}

output "recordings_account_name" {
  value = module.recordings.account_name
}

output "deadletter_storage_account_name" {
  value = try(module.deadletter[0].account_name, null)
}

output "system_topic_name" {
  value = try(module.blobevents[0].system_topic_name, null)
}

output "cosmos_endpoint" {
  value = try(module.cosmos[0].endpoint, null)
}

output "function_app_name" {
  value = try(module.functionapp[0].name, null)
}

output "function_app_hostname" {
  value = try(module.functionapp[0].default_hostname, null)
}

output "openai_base_url" {
  value = try(module.openai[0].base_url, null)
}

output "speech_endpoint" {
  value = try(module.speech[0].endpoint, null)
}

# Names only (values are endpoints and ids). The Function App's app_settings are unknown in a plan (azurerm can't
# plan a map with any unknown value), so the policy gate checks these names instead (Project 3 D18).
output "app_setting_names" {
  value = var.components.function_app ? module.functionapp[0].app_setting_names : sort(keys(local.app_settings))
}

# Non-secret settings for the laptop scripts as the operator (M7).
output "client_settings" {
  value = local.client_settings
}
