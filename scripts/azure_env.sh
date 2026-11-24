#!/usr/bin/env bash
# The deployed stack's laptop settings (D49), from its Terraform outputs in the shared remote state: writes
# ~/meet-azure.env with one `export NAME='value'` line per client setting, plus FUNCTION_URL. Endpoints and names
# only: the laptop scripts sign in as you (az login) with the operator's roles. Never the Speech settings (the
# laptop's Whisper run would switch to Speech, D44) and never a key; this script refuses to write either.
#
# Usage: ./scripts/azure_env.sh      then, in every shell that talks to Azure:   source ~/meet-azure.env
# Reads the state only (no plan, no refresh): no key is listed. Run it after the first apply of a session.
set -euo pipefail
cd "$(dirname "$0")/.."
LOCAL=infra/envs/local
AZURE=infra/envs/azure
OUT=${MEET_AZURE_ENV:-$HOME/meet-azure.env}

# Same init as `iac.sh plan-azure`: providers from envs/local, only the state account needs the network.
[[ -d $LOCAL/.terraform/providers ]] || terraform -chdir="$LOCAL" init -input=false -no-color >/dev/null
terraform -chdir="$AZURE" init -input=false -no-color -backend-config=backend.hcl \
  -plugin-dir="$PWD/$LOCAL/.terraform/providers" >/dev/null

summary=$(terraform -chdir="$AZURE" output -no-color -json summary 2>/dev/null) || {
  echo "FAIL no outputs in the remote state: is the stack deployed (./scripts/ci-deploy.sh apply)?"
  exit 1
}
[[ $(jq -r '.client_settings.COSMOS_ENDPOINT // ""' <<<"$summary") == https://* ]] || {
  echo "FAIL client_settings has no Cosmos endpoint: is the stack deployed?"
  exit 1
}
bad=$(jq -r '.client_settings | keys[] | select(test("^(SPEECH_|STT_|AZURE_CLIENT_ID$)") or test("(?i)(key|secret|password|connectionstring)$"))' <<<"$summary")
[[ -z $bad ]] || { echo "FAIL client_settings would set $bad on the laptop (D49)"; exit 1; }

{
  echo "# The meeting-summarizer Azure stack's laptop settings, written $(date -u +%Y-%m-%dT%H:%MZ) by scripts/azure_env.sh"
  jq -r '.client_settings | to_entries[] | "export \(.key)=\(.value | @sh)"' <<<"$summary"
  jq -r '"export FUNCTION_URL=\("https://" + .function_app_hostname | @sh)"' <<<"$summary"
} >"$OUT"
chmod 600 "$OUT"
echo "wrote $OUT: $(grep -c '^export ' "$OUT") settings ($(grep '^export ' "$OUT" | sed -E 's/^export ([A-Za-z_]+)=.*/\1/' | LC_ALL=C sort | tr '\n' ' '))"