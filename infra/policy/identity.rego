# Managed identity everywhere (D40). No local auth (keys, SAS, connection strings) on any data service, TLS 1.2
# minimum, and no secret-bearing app settings.
package main

import rego.v1

deny contains msg if {
	some rc in resources("azurerm_storage_account")
	rc.change.after.shared_access_key_enabled != false
	msg := sprintf("%s: storage Shared Key auth must be disabled", [rc.address])
}

deny contains msg if {
	some rc in resources("azurerm_storage_account")
	rc.change.after.allow_nested_items_to_be_public != false
	msg := sprintf("%s: anonymous blob access must be disabled", [rc.address])
}

deny contains msg if {
	some rc in resources("azurerm_storage_account")
	rc.change.after.min_tls_version != "TLS1_2"
	msg := sprintf("%s: storage minimum TLS must be TLS1_2", [rc.address])
}

deny contains msg if {
	some rc in resources("azurerm_storage_account")
	rc.change.after.https_traffic_only_enabled != true
	msg := sprintf("%s: storage must be HTTPS-only", [rc.address])
}

deny contains msg if {
	some rc in resources("azurerm_storage_container")
	rc.change.after.container_access_type != "private"
	msg := sprintf("%s: containers are private (recordings are meetings)", [rc.address])
}

deny contains msg if {
	some rc in resources("azurerm_cosmosdb_account")
	rc.change.after.local_authentication_enabled != false
	msg := sprintf("%s: Cosmos DB key auth must be disabled (local_authentication_enabled = false)", [rc.address])
}

deny contains msg if {
	some rc in resources("azurerm_cosmosdb_account")
	rc.change.after.access_key_metadata_writes_enabled != false
	msg := sprintf("%s: Cosmos DB metadata writes through account keys must be disabled", [rc.address])
}

deny contains msg if {
	some rc in resources("azurerm_cosmosdb_account")
	rc.change.after.minimal_tls_version != "Tls12"
	msg := sprintf("%s: Cosmos DB minimum TLS must be 1.2", [rc.address])
}

deny contains msg if {
	some rc in resources("azurerm_application_insights")
	rc.change.after.local_authentication_enabled != false
	msg := sprintf("%s: Application Insights ingestion must require Entra ID", [rc.address])
}

deny contains msg if {
	some rc in resources("azurerm_cognitive_account")
	rc.change.after.local_auth_enabled != false
	msg := sprintf("%s: Cognitive Services key auth must be disabled (local_auth_enabled = false)", [rc.address])
}

deny contains msg if {
	some rc in resources("azurerm_cognitive_account")
	object.get(rc.change.after, "custom_subdomain_name", null) in {null, ""}
	object.get(rc.change, ["after_unknown", "custom_subdomain_name"], false) != true # known only after apply: fine
	msg := sprintf("%s: a custom subdomain is required for Entra ID tokens", [rc.address])
}

# Batch transcription reads the recordings with the Speech account's own identity, and only a system-assigned one
# is supported for that (D3).
deny contains msg if {
	some rc in resources("azurerm_cognitive_account")
	rc.change.after.kind == "SpeechServices"
	not "SystemAssigned" in {i.type | some i in object.get(rc.change.after, "identity", [])}
	msg := sprintf("%s: the Speech account needs a system-assigned identity to read recordings without SAS (D3)", [rc.address])
}

# App settings: the Function App's map is unknown in a plan, so the stack outputs the names it will set.
# A plain connection-string setting, or anything named like a key or secret, is a credential in config.
forbidden_setting(name) if name in {"AzureWebJobsStorage", "RecordingsStorage", "COSMOS_KEY", "OPENAI_API_KEY"}

forbidden_setting(name) if regex.match(`(?i)(key|secret|password|connectionstring)$`, name)

deny contains msg if {
	some name in input.output_changes.summary.after.app_setting_names
	forbidden_setting(name)
	msg := sprintf("app setting %s: credentials in app settings are not allowed; use identity-based settings", [name])
}

deny contains msg if {
	not input.output_changes.summary.after.app_setting_names
	msg := "output summary.app_setting_names missing: the app settings gate can't run"
}

# The Blob trigger and the job reach the recordings through an identity-based connection (D17): without these the
# host would fall back to looking for a connection string.
required_settings := {
	"AzureWebJobsStorage__accountName",
	"AzureWebJobsStorage__credential",
	"RecordingsStorage__blobServiceUri",
	"RecordingsStorage__queueServiceUri",
	"RecordingsStorage__credential",
	"RecordingsStorage__clientId",
}

deny contains msg if {
	names := {n | some n in input.output_changes.summary.after.app_setting_names}
	resources("azurerm_function_app_flex_consumption") != []
	some needed in required_settings
	not needed in names
	msg := sprintf("app setting %s missing: the trigger's identity-based connection is incomplete (D17)", [needed])
}