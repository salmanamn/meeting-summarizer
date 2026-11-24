#!/usr/bin/env bash
# What the Azure evening actually cost (D48): Cost Management's actual cost of rg-meet-azure per meter category, then
# the total. Charges arrive 8-48 hours after use: run it the day after the session, and once more two days later.
# From Project 4's cost.sh.
#   ./scripts/cost.sh FROM_DATE [TO_DATE]        dates as YYYY-MM-DD (UTC); TO_DATE defaults to today
set -euo pipefail
FROM=${1:?usage: $0 FROM_DATE [TO_DATE]}
TO=${2:-$(date -u +%Y-%m-%d)}
RG=${RESOURCE_GROUP:-rg-meet-azure}
SUB=$(az account show --query id -o tsv)
BODY=$(jq -cn --arg from "${FROM}T00:00:00Z" --arg to "${TO}T23:59:59Z" --arg rg "$RG" '{
  type: "ActualCost", timeframe: "Custom", timePeriod: {from: $from, to: $to},
  dataset: {
    granularity: "None",
    aggregation: {cost: {name: "Cost", function: "Sum"}},
    grouping: [{type: "Dimension", name: "ResourceGroupName"}, {type: "Dimension", name: "MeterCategory"}],
    filter: {dimensions: {name: "ResourceGroupName", operator: "In", values: [$rg]}}
  }}')
RESULT=$(az rest --method post --body "$BODY" \
  --url "https://management.azure.com/subscriptions/$SUB/providers/Microsoft.CostManagement/query?api-version=2023-11-01")
echo "actual cost $FROM .. $TO (UTC), resource group $RG"
# Columns by name (Cost Management decides their order): Cost, ResourceGroupName, MeterCategory, Currency.
# shellcheck disable=SC2016 # a jq program: $p and $i are jq variables
TABLE='.properties as $p | ($p.columns | map(.name) | to_entries | map({(.value): .key}) | add) as $i
  | $p.rows | map({cost: .[$i.Cost], rg: .[$i.ResourceGroupName], meter: .[$i.MeterCategory], cur: .[$i.Currency]})'
jq -r "$TABLE"' | .[] | "\(.cost * 100 | round / 100)\t\(.cur)\t\(.rg)\t\(.meter)"' <<<"$RESULT" |
  awk -F'\t' '{printf "%8.2f %s  %-16s %s\n", $1, $2, $3, $4}'
jq -r "$TABLE"' | "total: \(map(.cost) | add // 0 | . * 100 | round / 100) \(.[0].cur // "")"' <<<"$RESULT"