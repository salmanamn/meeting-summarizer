#!/usr/bin/env bash
# Mask what goes into docs/evidence on its way there (M9): the subscription id, the signed-in user's name (the UPN or
# e-mail of `az account show`) and the last octet of every IPv4 address. A filter, so the command that writes an
# evidence file masks it:   <command> | ./scripts/mask_evidence.sh > docs/evidence/<file>
# Then check: grep -c '@' docs/evidence/<file>  ->  0 (no sign-in name left; evidence files carry no image digests).
set -euo pipefail
escape() { printf '%s' "$1" | sed -e 's/[]\/$*.^[+?(){}|]/\\&/g'; } # a literal in an extended regex
SUB=$(az account show --query id -o tsv)
UPN=$(az account show --query user.name -o tsv)
[[ -n $SUB && -n $UPN ]] || { echo "mask_evidence.sh: az account show gave no subscription or user" >&2; exit 1; }
sed -E -e "s/$(escape "$SUB")/<subscription>/g" -e "s/$(escape "$UPN")/<operator>/g" \
  -e 's/\b([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.)[0-9]{1,3}\b/\1x/g'