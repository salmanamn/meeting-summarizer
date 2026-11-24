#!/usr/bin/env bash
# The Azure evening as seen in log-slz-platform (Project 1): the Function App's App Insights tables, the resource logs
# of everything in rg-meet-azure, and who read and wrote the recordings account (the app, the Speech account's own
# identity, or you). Read-only queries as you (az login), via the Log Analytics API. From Project 3's telemetry.sh.
#
# Usage: scripts/telemetry.sh <start, ISO 8601 UTC> [meeting id prefix, default m7-]
# Run it while the stack is still up (it looks up the identities' object ids). Ingestion lags: App Insights 2-5 min,
# resource logs 5-15 min after the events.
set -euo pipefail
START=${1:?usage: telemetry.sh <start e.g. 2026-11-25T18:00:00Z> [meeting id prefix]}
PREFIX=${2:-m7-}
RG=${RESOURCE_GROUP:-rg-meet-azure}
[[ $START =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]] || { echo "start must look like 2026-11-25T18:00:00Z"; exit 2; }
[[ $PREFIX =~ ^[a-z0-9-]+$ ]] || { echo "prefix: lower-case letters, digits and hyphens only"; exit 2; }

WS=$(az monitor log-analytics workspace show -g rg-slz-platform -n log-slz-platform --query customerId -o tsv)
APP_OID=$(az identity show -g "$RG" -n id-meet-azure-app --query principalId -o tsv 2>/dev/null || true)
SPEECH_OID=$(az cognitiveservices account list -g "$RG" --query "[?kind=='SpeechServices'].identity.principalId | [0]" -o tsv 2>/dev/null || true)
ME_OID=$(az ad signed-in-user show --query id -o tsv)
WHEN="TimeGenerated between (datetime($START) .. now())"
STACK="_ResourceId contains '/resourcegroups/$RG/'"

query() {
  echo "== $1"
  az rest --method post --url "https://api.loganalytics.io/v1/workspaces/$WS/query" \
    --resource https://api.loganalytics.io --body "$(jq -n --arg q "$2" '{query: $q}')" --output json |
    jq -r '.tables[0] | ([.columns[].name] | @tsv), (.rows[] | map(tostring) | @tsv)' | table
  echo
}

table() { if command -v column >/dev/null; then column -t -s $'\t'; else cat; fi; }

query "Function executions (AppRequests)" \
  "AppRequests | where $WHEN | summarize runs = count(), failed = countif(Success == false), p50_ms = round(percentile(DurationMs, 50)), max_ms = round(max(DurationMs)) by Name | order by Name asc"
query "Job log lines for $PREFIX meetings (AppTraces)" \
  "AppTraces | where $WHEN | where Message has '$PREFIX' | project TimeGenerated, SeverityLevel, Message | order by TimeGenerated asc | take 60"
query "Exceptions (AppExceptions)" \
  "AppExceptions | where $WHEN | summarize count() by OperationName, ExceptionType, OuterMessage = substring(OuterMessage, 0, 120)"
query "Resource logs of $RG by table" \
  "union isfuzzy=true withsource=Table AzureDiagnostics, CDBDataPlaneRequests, StorageBlobLogs, StorageQueueLogs, FunctionAppLogs, AEGDeliveryFailureLogs, AEGDataPlaneRequests | where $WHEN | where $STACK | summarize rows = count() by Table | order by Table asc"
query "AzureDiagnostics by provider and category (Speech and Azure OpenAI are COGNITIVESERVICES)" \
  "AzureDiagnostics | where $WHEN | where $STACK | summarize rows = count() by ResourceProvider, Resource, Category | order by ResourceProvider asc, Resource asc"
query "Recordings account: blob operations by caller (Speech must read incoming/ with its own identity, D3)" \
  "StorageBlobLogs | where $WHEN | where $STACK | where AccountName startswith 'strec'
  | extend Caller = case(RequesterObjectId == '$APP_OID', 'app identity', RequesterObjectId == '$SPEECH_OID', 'speech account',
      RequesterObjectId == '$ME_OID', 'operator', isempty(RequesterObjectId), strcat('no identity (', AuthenticationType, ')'), 'other')
  | extend Container = tostring(split(ObjectKey, '/')[2])
  | summarize requests = count(), failed = countif(StatusText !in ('Success', 'BlobNotFound')) by Caller, OperationName, Container, AuthenticationType
  | order by Caller asc, OperationName asc"
query "Event Grid deliveries that failed (AEGDeliveryFailureLogs)" \
  "union isfuzzy=true AEGDeliveryFailureLogs | where $WHEN | where $STACK | summarize count() by Message = substring(Message, 0, 120)"