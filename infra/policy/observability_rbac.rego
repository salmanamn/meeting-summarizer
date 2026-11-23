# Diagnostics to log-slz-platform for every resource with resource logs, and a closed list of data-plane roles,
# each for the principal it is meant for (D42).
package main

import rego.v1

# --- Diagnostics -------------------------------------------------------------------------------

# Resource types that must have a diagnostic setting in the same module.
monitored := {
	"azurerm_cosmosdb_account",
	"azurerm_eventgrid_system_topic",
	"azurerm_function_app_flex_consumption",
	"azurerm_storage_account",
	"azurerm_cognitive_account",
}

diag_modules := {object.get(rc, "module_address", "") | some rc in resources("azurerm_monitor_diagnostic_setting")}

deny contains msg if {
	some type in monitored
	some rc in resources(type)
	not object.get(rc, "module_address", "") in diag_modules
	msg := sprintf("%s: no diagnostic setting in %s", [rc.address, object.get(rc, "module_address", "root")])
}

deny contains msg if {
	some rc in resources("azurerm_monitor_diagnostic_setting")
	not is_platform_workspace(rc.change.after.log_analytics_workspace_id)
	msg := sprintf("%s: diagnostics must go to log-slz-platform", [rc.address])
}

deny contains msg if {
	some rc in resources("azurerm_monitor_diagnostic_setting")
	not "allLogs" in {l.category_group | some l in rc.change.after.enabled_log}
	msg := sprintf("%s: enable category group allLogs", [rc.address])
}

deny contains msg if {
	some rc in resources("azurerm_application_insights")
	not is_platform_workspace(rc.change.after.workspace_id)
	msg := sprintf("%s: Application Insights must be workspace-based on log-slz-platform", [rc.address])
}

# --- RBAC --------------------------------------------------------------------------------------

# Every Azure role the stack may assign. Project 1's bootstrap lets the apply identity assign exactly these and the
# other projects' (its ABAC list); this list is the narrower one for this repository.
allowed_roles := {
	"b7e6dc6d-f1e8-4753-8033-0f276bb0955b", # Storage Blob Data Owner (host storage; the trigger's recordings connection)
	"974c5e8b-45b9-4653-ba55-5f855dd0fb88", # Storage Queue Data Contributor (the blob trigger's queues)
	"ba92f5b4-2d11-453d-a403-e96b0029c9fe", # Storage Blob Data Contributor (Event Grid dead-letters; the operator's uploads)
	"2a2b9908-6ea1-4ae2-8e65-a410df84e7d1", # Storage Blob Data Reader (the Speech account reads incoming/)
	"3913510d-42f4-4e42-8a64-420c390055eb", # Monitoring Metrics Publisher
	"5e0bd9bd-7b93-4f28-af87-19fc36ad61bd", # Cognitive Services OpenAI User
	"f2dc8367-1007-4938-bd23-fe263f013447", # Cognitive Services Speech User
}

# The only role a human (the operator, D42) may get from this stack: uploading meetings.
operator_roles := {"ba92f5b4-2d11-453d-a403-e96b0029c9fe"}

role_guid(rc) := guid if {
	parts := split(rc.change.after.role_definition_id, "/")
	guid := parts[count(parts) - 1]
}

deny contains msg if {
	some rc in resources("azurerm_role_assignment")
	not role_guid(rc) in allowed_roles
	msg := sprintf("%s: role %v is not on the data-plane allowlist", [rc.address, object.get(rc.change.after, "role_definition_id", "<by name>")])
}

deny contains msg if {
	some rc in resources("azurerm_role_assignment")
	not principal_allowed(rc)
	msg := sprintf("%s: roles go to managed identities (ServicePrincipal); a User only gets Storage Blob Data Contributor", [rc.address])
}

principal_allowed(rc) if rc.change.after.principal_type == "ServicePrincipal"

principal_allowed(rc) if {
	rc.change.after.principal_type == "User"
	role_guid(rc) in operator_roles
}

# A scope known at plan time must be a resource, never a subscription or resource group.
deny contains msg if {
	some rc in resources("azurerm_role_assignment")
	scope := rc.change.after.scope
	is_string(scope)
	regex.match(`^/subscriptions/[^/]+(/resourceGroups/[^/]+)?/?$`, scope)
	msg := sprintf("%s: scope %s is too broad", [rc.address, scope])
}

# Cosmos data plane: Built-in Data Contributor for the app, Built-in Data Reader for anyone else; database scope.
cosmos_contributor := "/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"

cosmos_reader := "/sqlRoleDefinitions/00000000-0000-0000-0000-000000000001"

deny contains msg if {
	some rc in resources("azurerm_cosmosdb_sql_role_assignment")
	id := rc.change.after.role_definition_id
	is_string(id)
	not endswith(id, cosmos_contributor)
	not endswith(id, cosmos_reader)
	msg := sprintf("%s: Cosmos role must be Built-in Data Contributor or Reader", [rc.address])
}

deny contains msg if {
	some rc in resources("azurerm_cosmosdb_sql_role_assignment")
	rc.name != "app"
	id := rc.change.after.role_definition_id
	is_string(id)
	not endswith(id, cosmos_reader)
	msg := sprintf("%s: only the app identity may write job records; anyone else reads", [rc.address])
}