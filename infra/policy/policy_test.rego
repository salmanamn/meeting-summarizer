# Run: conftest verify --policy infra/policy/
# A minimal plan with one compliant resource of each type passes; each test breaks one property.
package main

import rego.v1

ws := "/subscriptions/s/resourceGroups/rg-slz-platform/providers/Microsoft.OperationalInsights/workspaces/log-slz-platform"

role(guid) := sprintf("/subscriptions/s/providers/Microsoft.Authorization/roleDefinitions/%s", [guid])

rc(module, type, name, after) := {
	"address": sprintf("%s.%s.%s", [module, type, name]),
	"module_address": module,
	"type": type,
	"name": name,
	"change": {"actions": ["create"], "after": after, "after_unknown": {}},
}

diag(module) := rc(module, "azurerm_monitor_diagnostic_setting", "d", {"log_analytics_workspace_id": ws, "enabled_log": [{"category": "", "category_group": "allLogs"}]})

account(rules) := {
	"shared_access_key_enabled": false, "allow_nested_items_to_be_public": false, "min_tls_version": "TLS1_2",
	"https_traffic_only_enabled": true, "network_rules": [rules],
}

plain_rules := {"default_action": "Allow", "bypass": ["None"], "private_link_access": []}

speech_rules := {"default_action": "Allow", "bypass": ["None"], "private_link_access": [{"endpoint_resource_id": "/spch"}]}

container(module, name) := rc(module, "azurerm_storage_container", name, {"name": name, "container_access_type": "private"})

host := "module.stack.module.storage"

rec := "module.stack.module.recordings"

dl := "module.stack.module.deadletter[0]"

ev := "module.stack.module.blobevents[0]"

subscription := {
	"included_event_types": ["Microsoft.Storage.BlobCreated"],
	"event_delivery_schema": "EventGridSchema",
	"subject_filter": [{"subject_begins_with": "/blobServices/default/containers/incoming/blobs/", "subject_ends_with": "/meeting.json", "case_sensitive": true}],
	"webhook_endpoint": [{"max_events_per_batch": 1}],
	"retry_policy": [{"max_delivery_attempts": 5, "event_time_to_live": 1440}],
	"dead_letter_identity": [{"type": "SystemAssigned"}],
	"storage_blob_dead_letter_destination": [{"storage_blob_container_name": "eventgrid-deadletter"}],
}

flex := {
	"runtime_name": "python", "runtime_version": "3.13", "storage_authentication_type": "UserAssignedIdentity",
	"https_only": true, "webdeploy_publish_basic_authentication_enabled": false,
	"site_config": [{"minimum_tls_version": "1.2"}],
}

speech := {
	"kind": "SpeechServices", "local_auth_enabled": false, "custom_subdomain_name": "spch-x",
	"outbound_network_access_restricted": true, "fqdns": ["strecmeetazureabcde.blob.core.windows.net"],
	"identity": [{"type": "SystemAssigned"}],
}

openai := {"kind": "OpenAI", "local_auth_enabled": false, "custom_subdomain_name": "oai-x", "outbound_network_access_restricted": true, "fqdns": []}

cosmos := {"local_authentication_enabled": false, "access_key_metadata_writes_enabled": false, "minimal_tls_version": "Tls12", "capabilities": [{"name": "EnableServerless"}]}

good_resources := [
	rc(host, "azurerm_storage_account", "this", account(plain_rules)), container(host, "app-package"), diag(host),
	rc(rec, "azurerm_storage_account", "this", account(speech_rules)), container(rec, "incoming"), container(rec, "transcripts"), diag(rec),
	rc(dl, "azurerm_storage_account", "this", account(plain_rules)), container(dl, "eventgrid-deadletter"), diag(dl),
	rc(ev, "azurerm_eventgrid_system_topic", "this", {"topic_type": "Microsoft.Storage.StorageAccounts"}), diag(ev),
	rc(ev, "azurerm_eventgrid_system_topic_event_subscription", "manifest", subscription),
	rc("module.stack.module.cosmos[0]", "azurerm_cosmosdb_account", "this", cosmos), diag("module.stack.module.cosmos[0]"),
	rc("module.stack.module.cosmos[0]", "azurerm_cosmosdb_sql_container", "jobs", {"partition_key_paths": ["/id"]}),
	rc("module.stack.module.functionapp[0]", "azurerm_function_app_flex_consumption", "this", flex), diag("module.stack.module.functionapp[0]"),
	rc("module.stack", "azurerm_application_insights", "this", {"local_authentication_enabled": false, "workspace_id": ws}),
	rc("module.stack.module.openai[0]", "azurerm_cognitive_account", "this", openai), diag("module.stack.module.openai[0]"),
	rc("module.stack.module.openai[0]", "azurerm_cognitive_deployment", "chat", {"sku": [{"name": "GlobalStandard", "capacity": 50}]}),
	rc("module.stack.module.speech[0]", "azurerm_cognitive_account", "this", speech), diag("module.stack.module.speech[0]"),
	rc("module.stack", "azurerm_role_assignment", "app", {"role_definition_id": role("b7e6dc6d-f1e8-4753-8033-0f276bb0955b"), "principal_type": "ServicePrincipal"}),
	rc("module.stack", "azurerm_role_assignment", "operator_upload", {"role_definition_id": role("ba92f5b4-2d11-453d-a403-e96b0029c9fe"), "principal_type": "User"}),
	rc("module.stack", "azurerm_cosmosdb_sql_role_assignment", "app", {"role_definition_id": "/a/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"}),
	rc("module.stack", "azurerm_cosmosdb_sql_role_assignment", "operator", {"role_definition_id": "/a/sqlRoleDefinitions/00000000-0000-0000-0000-000000000001"}),
]

settings := [
	"AZURE_CLIENT_ID", "AzureWebJobsStorage__accountName", "AzureWebJobsStorage__clientId", "AzureWebJobsStorage__credential",
	"COSMOS_ENDPOINT", "RecordingsStorage__blobServiceUri", "RecordingsStorage__clientId",
	"RecordingsStorage__credential", "RecordingsStorage__queueServiceUri",
]

plan_of(resources, names) := {"resource_changes": resources, "output_changes": {"summary": {"after": {"app_setting_names": names}}}}

good := plan_of(good_resources, settings)

# Replace the `after` of the resource at `address` with `after` merged with `patch`.
with_patch(address, patch) := plan_of([r |
	some x in good_resources
	r := patched(x, address, patch)
], settings)

patched(x, address, patch) := object.union(x, {"change": {"after": object.union(x.change.after, patch)}}) if x.address == address

patched(x, address, _) := x if x.address != address

denied(plan, fragment) if {
	some msg in deny with input as plan
	contains(msg, fragment)
}

sub := "module.stack.module.blobevents[0].azurerm_eventgrid_system_topic_event_subscription.manifest"

speech_address := "module.stack.module.speech[0].azurerm_cognitive_account.this"

test_good_plan_passes if {
	count(deny) == 0 with input as good
}

test_shared_key if denied(with_patch("module.stack.module.storage.azurerm_storage_account.this", {"shared_access_key_enabled": true}), "Shared Key")

test_public_container if denied(with_patch("module.stack.module.recordings.azurerm_storage_container.incoming", {"container_access_type": "blob"}), "private")

test_trusted_services_bypass if {
	rules := object.union(plain_rules, {"bypass": ["AzureServices"]})
	denied(with_patch("module.stack.module.storage.azurerm_storage_account.this", {"network_rules": [rules]}), "bypass")
}

test_only_recordings_trust_a_resource_instance if denied(with_patch("module.stack.module.storage.azurerm_storage_account.this", {"network_rules": [speech_rules]}), "only the recordings account")

test_recordings_trust_the_speech_account if denied(with_patch("module.stack.module.recordings.azurerm_storage_account.this", {"network_rules": [plain_rules]}), "exactly one resource instance")

test_recordings_hold_only_their_containers if {
	plan := plan_of(array.concat(good_resources, [container(rec, "app-package")]), settings)
	denied(plan, "incoming/ and transcripts/ only")
}

test_deadletter_account_holds_nothing_else if {
	plan := plan_of(array.concat(good_resources, [container(dl, "transcripts")]), settings)
	denied(plan, "account of their own")
}

test_cosmos_keys if denied(with_patch("module.stack.module.cosmos[0].azurerm_cosmosdb_account.this", {"local_authentication_enabled": true}), "key auth")

test_cosmos_serverless if denied(with_patch("module.stack.module.cosmos[0].azurerm_cosmosdb_account.this", {"capabilities": []}), "serverless")

test_jobs_partition_key if denied(with_patch("module.stack.module.cosmos[0].azurerm_cosmosdb_sql_container.jobs", {"partition_key_paths": ["/stage"]}), "/id")

test_topic_source if denied(with_patch("module.stack.module.blobevents[0].azurerm_eventgrid_system_topic.this", {"topic_type": "Microsoft.Resources.Subscriptions"}), "system topic")

test_event_types if denied(with_patch(sub, {"included_event_types": ["Microsoft.Storage.BlobCreated", "Microsoft.Storage.BlobDeleted"]}), "BlobCreated only")

test_subject_filter if {
	f := [{"subject_begins_with": "/blobServices/default/containers/incoming/blobs/", "subject_ends_with": "", "case_sensitive": true}]
	denied(with_patch(sub, {"subject_filter": f}), "/meeting.json")
}

test_subject_filter_case if {
	f := [{"subject_begins_with": "/blobServices/default/containers/incoming/blobs/", "subject_ends_with": "/meeting.json", "case_sensitive": false}]
	denied(with_patch(sub, {"subject_filter": f}), "case-sensitive")
}

test_event_schema if denied(with_patch(sub, {"event_delivery_schema": "CloudEventSchemaV1_0"}), "Event Grid schema")

test_webhook_endpoint if denied(with_patch(sub, {"webhook_endpoint": []}), "webhook endpoint")

test_retries if denied(with_patch(sub, {"retry_policy": [{"max_delivery_attempts": 30, "event_time_to_live": 1440}]}), "at most 5")

test_deadletter_destination if denied(with_patch(sub, {"storage_blob_dead_letter_destination": []}), "dead-lettered")

test_deadletter_identity if denied(with_patch(sub, {"dead_letter_identity": []}), "managed identity")

test_flex_runtime if denied(with_patch("module.stack.module.functionapp[0].azurerm_function_app_flex_consumption.this", {"runtime_version": "3.12"}), "python 3.13")

test_flex_basic_auth if denied(with_patch("module.stack.module.functionapp[0].azurerm_function_app_flex_consumption.this", {"webdeploy_publish_basic_authentication_enabled": true}), "basic-auth")

test_appinsights_local_auth if denied(with_patch("module.stack.azurerm_application_insights.this", {"local_authentication_enabled": true}), "Entra ID")

test_openai_keys if denied(with_patch("module.stack.module.openai[0].azurerm_cognitive_account.this", {"local_auth_enabled": true}), "key auth")

test_openai_calls_nothing if denied(with_patch("module.stack.module.openai[0].azurerm_cognitive_account.this", {"fqdns": ["example.com"]}), "may call nothing")

test_speech_identity if denied(with_patch(speech_address, {"identity": [{"type": "UserAssigned"}]}), "system-assigned")

test_speech_outbound if denied(with_patch(speech_address, {"outbound_network_access_restricted": false}), "restricted")

test_speech_one_host if denied(with_patch(speech_address, {"fqdns": []}), "exactly one host")

test_speech_the_recordings_host if denied(with_patch(speech_address, {"fqdns": ["example.com"]}), "not the recordings account")

test_speech_unknown_fqdns_pass if {
	unknown := object.union(rc("module.stack.module.speech[0]", "azurerm_cognitive_account", "this", object.remove(speech, ["fqdns"])), {"change": {"after_unknown": {"fqdns": true}}})
	plan := plan_of(array.concat([r | some r in good_resources; r.address != speech_address], [unknown]), settings)
	count(deny) == 0 with input as plan
}

test_provisioned if denied(with_patch("module.stack.module.openai[0].azurerm_cognitive_deployment.chat", {"sku": [{"name": "ProvisionedManaged", "capacity": 50}]}), "provisioned")

test_missing_diagnostics if {
	plan := plan_of([r | some r in good_resources; r.address != "module.stack.module.cosmos[0].azurerm_monitor_diagnostic_setting.d"], settings)
	denied(plan, "no diagnostic setting")
}

test_role_not_allowed if denied(with_patch("module.stack.azurerm_role_assignment.app", {"role_definition_id": role("8e3af657-a8ff-443c-a75c-2fe8c4bcb635")}), "allowlist")

test_user_gets_only_upload if denied(with_patch("module.stack.azurerm_role_assignment.app", {"principal_type": "User"}), "a User only gets")

test_role_scope if denied(with_patch("module.stack.azurerm_role_assignment.app", {"scope": "/subscriptions/s/resourceGroups/rg-meet-azure"}), "too broad")

test_operator_reads_jobs if denied(with_patch("module.stack.azurerm_cosmosdb_sql_role_assignment.operator", {"role_definition_id": "/a/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"}), "only the app identity")

test_connection_string_setting if denied(plan_of(good_resources, array.concat(settings, ["RecordingsStorage"])), "credentials in app settings")

test_key_setting if denied(plan_of(good_resources, array.concat(settings, ["SPEECH_KEY"])), "credentials in app settings")

test_trigger_connection_complete if denied(plan_of(good_resources, [n | some n in settings; n != "RecordingsStorage__clientId"]), "RecordingsStorage__clientId missing")