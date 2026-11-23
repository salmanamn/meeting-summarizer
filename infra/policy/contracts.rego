# Contracts the application code depends on: the manifest event (D15, D40), the job records (D17), the Flex
# Consumption host (D12) and the Speech account's access to the recordings (D3, D41).
package main

import rego.v1

# --- Event Grid: the manifest subscription ----------------------------------------------------

deny contains msg if {
	some rc in resources("azurerm_eventgrid_system_topic")
	rc.change.after.topic_type != "Microsoft.Storage.StorageAccounts"
	msg := sprintf("%s: the topic must be the recordings account's system topic", [rc.address])
}

deny contains msg if {
	some rc in resources("azurerm_eventgrid_system_topic_event_subscription")
	rc.change.after.included_event_types != ["Microsoft.Storage.BlobCreated"]
	msg := sprintf("%s: BlobCreated only (D15)", [rc.address])
}

deny contains msg if {
	some rc in resources("azurerm_eventgrid_system_topic_event_subscription")
	rc.change.after.event_delivery_schema != "EventGridSchema"
	msg := sprintf("%s: the blobs extension's webhook reads the Event Grid schema", [rc.address])
}

# Only manifests may reach the Function: in Event Grid mode the trigger's path is not a filter (D15).
deny contains msg if {
	some rc in resources("azurerm_eventgrid_system_topic_event_subscription")
	not manifest_filter_ok(rc.change.after)
	msg := sprintf("%s: subject must begin /blobServices/default/containers/incoming/blobs/ and end /meeting.json, case-sensitive (D15)", [rc.address])
}

manifest_filter_ok(a) if {
	[f] := a.subject_filter
	f.subject_begins_with == "/blobServices/default/containers/incoming/blobs/"
	f.subject_ends_with == "/meeting.json"
	f.case_sensitive == true
}

deny contains msg if {
	some rc in resources("azurerm_eventgrid_system_topic_event_subscription")
	count(object.get(rc.change.after, "webhook_endpoint", [])) != 1
	msg := sprintf("%s: the Event Grid-based Blob trigger takes a webhook endpoint (/runtime/webhooks/blobs, D40)", [rc.address])
}

deny contains msg if {
	some rc in resources("azurerm_eventgrid_system_topic_event_subscription")
	some p in rc.change.after.retry_policy
	p.max_delivery_attempts > 5
	msg := sprintf("%s: at most 5 delivery attempts, as the local stub (D15)", [rc.address])
}

deny contains msg if {
	some rc in resources("azurerm_eventgrid_system_topic_event_subscription")
	count(object.get(rc.change.after, "storage_blob_dead_letter_destination", [])) == 0
	msg := sprintf("%s: undeliverable manifest events must be dead-lettered to blob", [rc.address])
}

deny contains msg if {
	some rc in resources("azurerm_eventgrid_system_topic_event_subscription")
	count(object.get(rc.change.after, "dead_letter_identity", [])) == 0
	msg := sprintf("%s: dead-lettering must use the topic's managed identity (storage has no keys)", [rc.address])
}

# The dead-letter container has a storage account of its own (Project 3 D25). Event Grid only accepts an
# account-scoped blob role for the topic identity (Project 3 D24), so that account must hold nothing else.
# Account ids are unknown at plan time and container names are not: one storage module instance is one account.
deadletter_container := "eventgrid-deadletter"

container_modules(name) := {object.get(rc, "module_address", "") |
	some rc in resources("azurerm_storage_container")
	rc.change.after.name == name
}

deny contains msg if {
	some rc in resources("azurerm_storage_container")
	object.get(rc, "module_address", "") in container_modules(deadletter_container)
	rc.change.after.name != deadletter_container
	msg := sprintf("%s: shares a storage account with the Event Grid dead-letter container; dead-letters get an account of their own (Project 3 D25)", [rc.address])
}

deny contains msg if {
	some rc in resources("azurerm_eventgrid_system_topic_event_subscription")
	some dest in object.get(rc.change.after, "storage_blob_dead_letter_destination", [])
	dest.storage_blob_container_name != deadletter_container
	msg := sprintf("%s: dead-letters go to the %s container, which has its own storage account", [rc.address, deadletter_container])
}

# --- The recordings account (D38) -------------------------------------------------------------

recordings_modules := container_modules("incoming")

# Recordings never share an account with the host's package or with dead-letters.
deny contains msg if {
	some rc in resources("azurerm_storage_container")
	object.get(rc, "module_address", "") in recordings_modules
	not rc.change.after.name in {"incoming", "transcripts"}
	msg := sprintf("%s: the recordings account holds incoming/ and transcripts/ only (D38)", [rc.address])
}

# A resource access rule names a trusted resource instance: only the recordings account has one, for Speech (D3).
deny contains msg if {
	some rc in resources("azurerm_storage_account")
	some rule in rc.change.after.network_rules
	count(object.get(rule, "private_link_access", [])) > 0
	not object.get(rc, "module_address", "") in recordings_modules
	msg := sprintf("%s: only the recordings account trusts a resource instance (the Speech account, D3)", [rc.address])
}

deny contains msg if {
	some rc in resources("azurerm_storage_account")
	some rule in rc.change.after.network_rules
	"AzureServices" in object.get(rule, "bypass", [])
	msg := sprintf("%s: no blanket trusted-services bypass; trust named resource instances instead (D39)", [rc.address])
}

deny contains msg if {
	speech_planned
	some rc in resources("azurerm_storage_account")
	object.get(rc, "module_address", "") in recordings_modules
	some rule in rc.change.after.network_rules
	count(object.get(rule, "private_link_access", [])) != 1
	msg := sprintf("%s: the recordings account trusts exactly one resource instance, the Speech account (D3)", [rc.address])
}

speech_planned if {
	some rc in resources("azurerm_cognitive_account")
	rc.change.after.kind == "SpeechServices"
}

# --- Cognitive Services: who the services themselves may call ---------------------------------

deny contains msg if {
	some rc in resources("azurerm_cognitive_account")
	rc.change.after.outbound_network_access_restricted != true
	msg := sprintf("%s: outbound access must be restricted (data loss prevention)", [rc.address])
}

deny contains msg if {
	some rc in resources("azurerm_cognitive_account")
	rc.change.after.kind == "OpenAI"
	count(object.get(rc.change.after, "fqdns", [])) != 0
	msg := sprintf("%s: Azure OpenAI may call nothing", [rc.address])
}

# Speech may call one host: the recordings account's blob endpoint (D41). The host name has the account's random
# letters in it, so in a plan of a new stack the list is unknown; a known list is checked by its length and shape
# (tests/unit/test_infra_contract.py checks the Terraform that builds it).
deny contains msg if {
	some rc in resources("azurerm_cognitive_account")
	rc.change.after.kind == "SpeechServices"
	object.get(rc.change, ["after_unknown", "fqdns"], false) != true # unknown until apply: shape checked below when known
	count(object.get(rc.change.after, "fqdns", [])) != 1
	msg := sprintf("%s: Speech may call exactly one host, the recordings account's blob endpoint (D41)", [rc.address])
}

deny contains msg if {
	some rc in resources("azurerm_cognitive_account")
	rc.change.after.kind == "SpeechServices"
	some fqdn in object.get(rc.change.after, "fqdns", [])
	is_string(fqdn)
	not regex.match(`^strec[a-z0-9]+\.blob\.core\.windows\.net$`, fqdn)
	msg := sprintf("%s: %s is not the recordings account's blob host (D41)", [rc.address, fqdn])
}

deny contains msg if {
	some rc in resources("azurerm_cognitive_deployment")
	some sku in rc.change.after.sku
	contains(sku.name, "Provisioned")
	msg := sprintf("%s: provisioned throughput (%s) is billed per hour whether used or not; use a Standard SKU", [rc.address, sku.name])
}

# --- Cosmos DB: serverless, the jobs container ------------------------------------------------

capabilities(rc) := {c.name | some c in rc.change.after.capabilities}

deny contains msg if {
	some rc in resources("azurerm_cosmosdb_account")
	not "EnableServerless" in capabilities(rc)
	msg := sprintf("%s: serverless (pay per request) for a lab that is idle most of the time", [rc.address])
}

deny contains msg if {
	some rc in resources("azurerm_cosmosdb_sql_container")
	rc.change.after.partition_key_paths != ["/id"]
	msg := sprintf("%s: jobs are partitioned by /id = meeting id: every access is a point read (D17)", [rc.address])
}

# --- Function App: Flex Consumption ---------------------------------------------------------

deny contains msg if {
	some rc in resources("azurerm_function_app_flex_consumption")
	not flex_runtime_ok(rc.change.after)
	msg := sprintf("%s: runtime must be python 3.13 (D12)", [rc.address])
}

flex_runtime_ok(a) if {
	a.runtime_name == "python"
	a.runtime_version == "3.13"
}

deny contains msg if {
	some rc in resources("azurerm_function_app_flex_consumption")
	rc.change.after.storage_authentication_type == "StorageAccountConnectionString"
	msg := sprintf("%s: deployment storage must use a managed identity, not a connection string", [rc.address])
}

deny contains msg if {
	some rc in resources("azurerm_function_app_flex_consumption")
	rc.change.after.https_only != true
	msg := sprintf("%s: HTTPS only", [rc.address])
}

deny contains msg if {
	some rc in resources("azurerm_function_app_flex_consumption")
	rc.change.after.webdeploy_publish_basic_authentication_enabled != false
	msg := sprintf("%s: basic-auth publishing credentials must be disabled", [rc.address])
}

deny contains msg if {
	some rc in resources("azurerm_function_app_flex_consumption")
	not rc.change.after.site_config[0].minimum_tls_version == "1.2"
	msg := sprintf("%s: minimum TLS must be 1.2", [rc.address])
}