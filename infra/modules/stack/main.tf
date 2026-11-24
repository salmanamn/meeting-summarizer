# Composition root: everything both environments deploy (D38).
# envs/local and envs/azure call only this module and differ ONLY in provider config and inputs.
terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm" }
    random  = { source = "hashicorp/random" }
  }
}

data "azurerm_client_config" "current" {}

# Storage, Cosmos, Function App, OpenAI and Speech names are global DNS names -> random suffix
resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
}

locals {
  suffixed = "${var.name}-${random_string.suffix.result}"
  compact  = "${replace(var.name, "-", "")}${random_string.suffix.result}"

  # The recordings account's name and blob host, built from names: the account trusts the Speech account and the
  # Speech account may call only this host, so taking either from the other resource would be a cycle (D41).
  recordings_account   = "strec${local.compact}"
  recordings_blob_host = "${local.recordings_account}.blob.${var.storage_suffix}"

  deployment_container  = "app-package"          # Flex Consumption deployment package
  incoming_container    = "incoming"             # incoming/<meeting-id>/ with meeting.json last (D15)
  transcripts_container = "transcripts"          # transcripts/<meeting-id>/<sha16>.<model>.json (D17)
  deadletter_container  = "eventgrid-deadletter" # manifest events Event Grid could not deliver
  manifest_name         = "meeting.json"

  blob_subscription = var.blob_subscription_enabled && var.components.eventgrid && var.components.function_app
}

resource "azurerm_resource_group" "this" {
  name     = "rg-${var.name}"
  location = var.location
  tags     = var.tags
}

# The one identity the app runs as. User-assigned, so its roles exist before the app starts (Project 3 D16).
resource "azurerm_user_assigned_identity" "app" {
  name                = "id-${var.name}-app"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = var.tags
}

# Host storage of the Function App: AzureWebJobsStorage (the blob trigger's queue) and the deployment package.
module "storage" {
  source                     = "../storage"
  name                       = "st${local.compact}"
  resource_group_name        = azurerm_resource_group.this.name
  location                   = azurerm_resource_group.this.location
  containers                 = [local.deployment_container]
  diagnostics_enabled        = var.diagnostics_enabled
  log_analytics_workspace_id = var.log_analytics_workspace_id
  tags                       = var.tags
}

# The recordings account (D38): what users upload and what the job writes back. Its own account, so the Speech
# identity's read role and the system topic's events reach recordings and nothing of the host's.
module "recordings" {
  source                     = "../storage"
  name                       = local.recordings_account
  resource_group_name        = azurerm_resource_group.this.name
  location                   = azurerm_resource_group.this.location
  containers                 = [local.incoming_container, local.transcripts_container]
  resource_instance_ids      = var.components.speech ? [module.speech[0].account_id] : []
  diagnostics_enabled        = var.diagnostics_enabled
  log_analytics_workspace_id = var.log_analytics_workspace_id
  tags                       = var.tags
}

# Event Grid dead-letters get a storage account of their own (Project 3 D25).
module "deadletter" {
  count                      = var.components.eventgrid ? 1 : 0
  source                     = "../storage"
  name                       = "stdl${local.compact}"
  resource_group_name        = azurerm_resource_group.this.name
  location                   = azurerm_resource_group.this.location
  containers                 = [local.deadletter_container]
  diagnostics_enabled        = var.diagnostics_enabled
  log_analytics_workspace_id = var.log_analytics_workspace_id
  tags                       = var.tags
}

module "cosmos" {
  count                      = var.components.cosmos ? 1 : 0
  source                     = "../cosmos"
  name                       = "cosmos-${local.suffixed}"
  resource_group_name        = azurerm_resource_group.this.name
  location                   = azurerm_resource_group.this.location
  database_name              = "meetings"
  jobs_container_name        = "jobs"
  diagnostics_enabled        = var.diagnostics_enabled
  log_analytics_workspace_id = var.log_analytics_workspace_id
  tags                       = var.tags
}

module "openai" {
  count                      = var.components.openai ? 1 : 0
  source                     = "../openai"
  name                       = "oai-${local.suffixed}"
  resource_group_name        = azurerm_resource_group.this.name
  location                   = azurerm_resource_group.this.location
  chat                       = var.chat_deployment
  diagnostics_enabled        = var.diagnostics_enabled
  log_analytics_workspace_id = var.log_analytics_workspace_id
  tags                       = var.tags
}

module "speech" {
  count                      = var.components.speech ? 1 : 0
  source                     = "../speech"
  name                       = "spch-${local.suffixed}"
  resource_group_name        = azurerm_resource_group.this.name
  location                   = azurerm_resource_group.this.location
  allowed_fqdns              = [local.recordings_blob_host]
  diagnostics_enabled        = var.diagnostics_enabled
  log_analytics_workspace_id = var.log_analytics_workspace_id
  tags                       = var.tags
}

# The blobs extension's system key, readable only once the code is deployed and the host has started (D40).
data "azurerm_function_app_host_keys" "app" {
  count               = local.blob_subscription ? 1 : 0
  name                = module.functionapp[0].name
  resource_group_name = azurerm_resource_group.this.name
}

module "blobevents" {
  count                         = var.components.eventgrid ? 1 : 0
  source                        = "../blobevents"
  name                          = "evgst-${local.suffixed}"
  resource_group_name           = azurerm_resource_group.this.name
  location                      = azurerm_resource_group.this.location
  subscription_id               = data.azurerm_client_config.current.subscription_id
  source_storage_account_id     = module.recordings.account_id
  incoming_container_name       = module.recordings.container_names[local.incoming_container]
  manifest_name                 = local.manifest_name
  subscription_enabled          = local.blob_subscription
  webhook_url                   = local.blob_subscription ? "https://${module.functionapp[0].default_hostname}/runtime/webhooks/blobs?functionName=Host.Functions.${var.trigger_function_name}&code=${data.azurerm_function_app_host_keys.app[0].blobs_extension_key}" : null
  max_delivery_attempts         = var.event_max_delivery_attempts
  deadletter_storage_account_id = module.deadletter[0].account_id
  deadletter_container_name     = module.deadletter[0].container_names[local.deadletter_container]
  role_assignments_enabled      = var.components.rbac
  diagnostics_enabled           = var.diagnostics_enabled
  log_analytics_workspace_id    = var.log_analytics_workspace_id
  tags                          = var.tags
}

locals {
  # Model and speech settings. Values are endpoints and deployment names: no keys (D40).
  openai_settings = var.components.openai ? {
    OPENAI_BASE_URL       = module.openai[0].base_url
    OPENAI_AUTH           = "entra" # read from M6: an Entra token provider instead of OPENAI_API_KEY (D41)
    CHAT_MODEL            = module.openai[0].chat_deployment
    CHAT_REASONING_EFFORT = var.chat_reasoning_effort
    SUMMARY_MAX_TOKENS    = tostring(var.summary_max_tokens)
  } : {}

  speech_settings = var.components.speech ? {
    SPEECH_ENDPOINT = module.speech[0].endpoint # read from M6 (the batch transcriber, D3)
    SPEECH_REGION   = module.speech[0].region
  } : {}

  # Endpoints and names only. src/meeting/settings.py reads the same names locally (D8, D17).
  app_settings = merge(
    {
      AZURE_CLIENT_ID = azurerm_user_assigned_identity.app.client_id # DefaultAzureCredential -> this identity

      # The Blob trigger's connection ("RecordingsStorage" in function_app.py) and the job's blob client: the same
      # settings, an identity-based connection. The queue URI is for the trigger's poison queue.
      RecordingsStorage__blobServiceUri  = module.recordings.primary_blob_endpoint
      RecordingsStorage__queueServiceUri = module.recordings.primary_queue_endpoint
      RecordingsStorage__credential      = "managedidentity"
      RecordingsStorage__clientId        = azurerm_user_assigned_identity.app.client_id
      INCOMING_CONTAINER                 = module.recordings.container_names[local.incoming_container]
      TRANSCRIPTS_CONTAINER              = module.recordings.container_names[local.transcripts_container]

      COSMOS_ENDPOINT       = var.components.cosmos ? module.cosmos[0].endpoint : ""
      COSMOS_DATABASE       = var.components.cosmos ? module.cosmos[0].database_name : "meetings"
      COSMOS_JOBS_CONTAINER = var.components.cosmos ? module.cosmos[0].jobs_container_name : "jobs"

      JOB_MAX_ATTEMPTS = tostring(var.job_max_attempts) # = host.json poisonBlobThreshold (a unit test checks)
    },
    local.openai_settings,
    local.speech_settings,
    var.extra_app_settings,
  )

  # What the laptop scripts need to reach the deployed stack as the operator (M7, D49): upload, read the record and
  # the transcript, summarise with the stack's chat deployment. Never the Speech settings: with SPEECH_ENDPOINT set
  # the laptop's Whisper run would switch to Speech (D44); never AZURE_CLIENT_ID: the laptop signs in as you.
  client_settings = merge(
    {
      RecordingsStorage__blobServiceUri = local.app_settings.RecordingsStorage__blobServiceUri
      INCOMING_CONTAINER                = local.app_settings.INCOMING_CONTAINER
      TRANSCRIPTS_CONTAINER             = local.app_settings.TRANSCRIPTS_CONTAINER
      COSMOS_ENDPOINT                   = local.app_settings.COSMOS_ENDPOINT
      COSMOS_DATABASE                   = local.app_settings.COSMOS_DATABASE
      COSMOS_JOBS_CONTAINER             = local.app_settings.COSMOS_JOBS_CONTAINER
    },
    local.openai_settings,
  )
}

# Workspace-based: telemetry lands in log-slz-platform next to the resource logs.
resource "azurerm_application_insights" "this" {
  count                        = var.components.function_app ? 1 : 0
  name                         = "appi-${local.suffixed}"
  resource_group_name          = azurerm_resource_group.this.name
  location                     = azurerm_resource_group.this.location
  application_type             = "other"
  workspace_id                 = var.log_analytics_workspace_id
  local_authentication_enabled = false # ingestion needs Entra (Monitoring Metrics Publisher)
  tags                         = var.tags
}

module "functionapp" {
  count                                  = var.components.function_app ? 1 : 0
  source                                 = "../functionapp"
  name                                   = local.suffixed
  resource_group_name                    = azurerm_resource_group.this.name
  location                               = azurerm_resource_group.this.location
  identity_id                            = azurerm_user_assigned_identity.app.id
  identity_client_id                     = azurerm_user_assigned_identity.app.client_id
  storage_account_name                   = module.storage.account_name
  storage_primary_blob_endpoint          = module.storage.primary_blob_endpoint
  deployment_container_name              = module.storage.container_names[local.deployment_container]
  maximum_instance_count                 = var.function_maximum_instance_count
  instance_memory_in_mb                  = var.function_instance_memory_in_mb
  application_insights_connection_string = azurerm_application_insights.this[0].connection_string
  app_settings                           = local.app_settings
  diagnostics_enabled                    = var.diagnostics_enabled
  log_analytics_workspace_id             = var.log_analytics_workspace_id
  tags                                   = var.tags

  # The host starts with its identity's data roles already in place (Project 3 D16)
  depends_on = [azurerm_role_assignment.app, azurerm_cosmosdb_sql_role_assignment.app]
}
