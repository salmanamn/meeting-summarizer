#!/usr/bin/env bash
# The Azure evening as seen in log-slz-platform (Project 1): the Function App's App Insights tables, the resource logs
# of everything in rg-meet-azure, and who read and wrote the recordings account (the app, the Speech account's own
# identity, or you). Read-only queries as you (az login), via the Log Analytics API. From Project 3's telemetry.sh.
#
# Usage: scripts/telemetry.sh <start, ISO 8601 UTC> [meeting id prefix, default m7-] [end, ISO 8601 UTC, default now]
# Ingestion lags: App Insights 2-5 min, resource logs 5-15 min after the events. The workspace keeps 90 days, so an
# evening can be read again after its destroy (M8, D51): the identities' object ids can't be looked up then, and
# their callers show as "other <first 8 characters of the object id>" with the user agent that tells them apart.
#
# M8 (D51): a query that fails prints "query failed: ..." and the script goes on (in M7 one failed query, under
# set -e, ended the script and hid three sections); the per-table counts are one query per table, not a union; the
# Azure SDKs' request/response dumps are left out of the job's log lines.
set -euo pipefail
START=${1:?usage: telemetry.sh <start e.g. 2026-11-25T18:00:00Z> [meeting id prefix] [end]}
PREFIX=${2:-m7-}
END=${3:-}
RG=${RESOURCE_GROUP:-rg-meet-azure}
ISO='^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$'
[[ $START =~ $ISO ]] || { echo "start must look like 2026-11-25T18:00:00Z"; exit 2; }
[[ -z $END || $END =~ $ISO ]] || { echo "end must look like 2026-11-25T18:00:00Z"; exit 2; }
[[ $PREFIX =~ ^[a-z0-9-]+$ ]] || { echo "prefix: lower-case letters, digits and hyphens only"; exit 2; }

WS=$(az monitor log-analytics workspace show -g rg-slz-platform -n log-slz-platform --query customerId -o tsv)
# Empty when the stack is gone: a value that matches no object id, never '' (that would match anonymous requests).
APP_OID=$(az identity show -g "$RG" -n id-meet-azure-app --query principalId -o tsv 2>/dev/null || true)
SPEECH_OID=$(az cognitiveservices account list -g "$RG" --query "[?kind=='SpeechServices'].identity.principalId | [0]" -o tsv 2>/dev/null || true)
APP_OID=${APP_OID:-not-looked-up}
SPEECH_OID=${SPEECH_OID:-not-looked-up}
ME_OID=$(az ad signed-in-user show --query id -o tsv)
UNTIL="now()"
[[ -z $END ]] || UNTIL="datetime($END)"
WHEN="TimeGenerated between (datetime($START) .. $UNTIL)"
STACK="_ResourceId contains '/resourcegroups/$RG/'"

echo "window: $START .. ${END:-now}; resource group $RG; identities looked up: app $([[ $APP_OID == not-looked-up ]] && echo no || echo yes), speech $([[ $SPEECH_OID == not-looked-up ]] && echo no || echo yes)"
echo

table() { if command -v column >/dev/null; then column -t -s $'\t'; else cat; fi; }

# run_query <kql>: the result as TSV with a header row, or exit 1 with the API's error on stderr
run_query() {
  az rest --method post --url "https://api.loganalytics.io/v1/workspaces/$WS/query" \
    --resource https://api.loganalytics.io --body "$(jq -n --arg q "$1" '{query: $q}')" --output json |
    jq -r '.tables[0] | ([.columns[].name] | @tsv), (.rows[] | map(tostring) | @tsv)'
}

query() {
  local out err
  echo "== $1"
  err=$(mktemp)
  if out=$(run_query "$2" 2>"$err"); then
    table <<<"$out"
  else
    echo "query failed: $(tr '\n' ' ' <"$err" | cut -c1-300)"
  fi
  rm -f "$err"
  echo
}

query "Function executions (AppRequests)" \
  "AppRequests | where $WHEN | summarize runs = count(), failed = countif(Success == false), p50_ms = round(percentile(DurationMs, 50)), max_ms = round(max(DurationMs)) by Name | order by Name asc"
query "Job log lines for $PREFIX meetings (AppTraces, without the SDKs' HTTP dumps)" \
  "AppTraces | where $WHEN | where Message has '$PREFIX'
  | where not(Message startswith 'Request URL:' or Message startswith 'Response status:' or Message startswith 'Request [' or Message startswith 'Response [')
  | project TimeGenerated, SeverityLevel, Message = substring(Message, 0, 200) | order by TimeGenerated asc | take 60"
query "Exceptions (AppExceptions), first and last of each" \
  "AppExceptions | where $WHEN | summarize count(), first = min(TimeGenerated), last = max(TimeGenerated) by OperationName, ExceptionType, OuterMessage = substring(OuterMessage, 0, 100) | order by first asc"

echo "== Resource logs of $RG by table (one query each)"
for t in AzureDiagnostics CDBDataPlaneRequests StorageBlobLogs StorageQueueLogs FunctionAppLogs AEGDeliveryFailureLogs AEGDataPlaneRequests; do
  if rows=$(run_query "$t | where $WHEN | where $STACK | count" 2>/dev/null | tail -n +2); then
    printf '%-24s %s\n' "$t" "$rows"
  else
    printf '%-24s %s\n' "$t" "query failed (table not in the workspace, or no _ResourceId)"
  fi
done
echo

query "AzureDiagnostics by provider and category (Speech and Azure OpenAI are COGNITIVESERVICES)" \
  "AzureDiagnostics | where $WHEN | where $STACK | summarize rows = count() by ResourceProvider, Resource, Category | order by ResourceProvider asc, Resource asc"
query "Recordings account: blob operations by caller (Speech must read incoming/ with its own identity, D3)" \
  "StorageBlobLogs | where $WHEN | where $STACK | where AccountName startswith 'strec'
  | extend Caller = case(RequesterObjectId == '$APP_OID', 'app identity', RequesterObjectId == '$SPEECH_OID', 'speech account',
      RequesterObjectId == '$ME_OID', 'operator', isempty(RequesterObjectId), strcat('no identity (', AuthenticationType, ')'),
      strcat('other ', substring(RequesterObjectId, 0, 8)))
  | extend Container = tostring(split(ObjectKey, '/')[2]), Agent = tostring(split(UserAgentHeader, ' ')[0])
  | summarize requests = count(), failed = countif(StatusText !in ('Success', 'BlobNotFound')) by Caller, OperationName, Container, AuthenticationType, Agent
  | order by Caller asc, OperationName asc"
query "Event Grid deliveries that failed (AEGDeliveryFailureLogs)" \
  "AEGDeliveryFailureLogs | where $WHEN | where $STACK | summarize count() by Message = substring(Message, 0, 120)"