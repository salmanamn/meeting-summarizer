output "account_id" {
  description = "The account's ARM id: the role scope and the recordings account's resource access rule"
  value       = azurerm_cognitive_account.this.id
}

output "endpoint" {
  description = "Custom-subdomain endpoint for the speech to text REST API with an Entra token (M6)"
  value       = "https://${azurerm_cognitive_account.this.custom_subdomain_name}.cognitiveservices.azure.com/"
}

output "principal_id" {
  description = "The system-assigned identity that reads the recordings (D3)"
  value       = azurerm_cognitive_account.this.identity[0].principal_id
}

output "region" {
  value = azurerm_cognitive_account.this.location
}
