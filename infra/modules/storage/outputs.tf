output "account_id" {
  value = azurerm_storage_account.this.id
}

output "account_name" {
  value = azurerm_storage_account.this.name
}

output "primary_blob_endpoint" {
  value = azurerm_storage_account.this.primary_blob_endpoint
}

output "primary_blob_host" {
  value = azurerm_storage_account.this.primary_blob_host
}

output "primary_queue_endpoint" {
  value = azurerm_storage_account.this.primary_queue_endpoint
}

# name => name, read from the created containers: whoever uses a name waits for its container.
output "container_names" {
  value = { for key, container in azurerm_storage_container.this : key => container.name }
}

# name => resource manager id: the scope of a role on one container.
output "container_ids" {
  value = { for key, container in azurerm_storage_container.this : key => container.id }
}
