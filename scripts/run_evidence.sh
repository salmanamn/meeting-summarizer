#!/usr/bin/env bash
# One GitHub Actions run's log lines as a markdown evidence block (M8, D51): a heading with the run id, then the lines
# matching an extended regex, fenced. The log is cleaned first, in this order:
#   1. gh's "job<TAB>step<TAB>" prefix and the timestamp go;
#   2. lines GitHub echoes for a step's commands (cyan, ESC[36;1m) go: M7's grep matched its own command lines;
#   3. every other ANSI colour code goes (terraform plan prints in colour in CI);
#   4. GitHub's "##[group]" / "##[endgroup]" markers go.
# Exit 1 when no line matches (an empty block is never evidence). Mask on the way to the file:
#   ./scripts/run_evidence.sh "E1 apply" <run id> 'Plan:|tests,|OK   |Apply complete' | ./scripts/mask_evidence.sh >> docs/evidence/<file>
set -euo pipefail
TITLE=${1:?usage: run_evidence.sh <title> <run id> <extended regex>}
RUN=${2:?usage: run_evidence.sh <title> <run id> <extended regex>}
PATTERN=${3:?usage: run_evidence.sh <title> <run id> <extended regex>}
[[ $RUN =~ ^[0-9]+$ ]] || { echo "run id: digits only" >&2; exit 2; }

ESC=$'\e'
LOG=$(gh run view "$RUN" --log)
LINES=$(cut -f3- <<<"$LOG" |
  sed -E 's/^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.]+Z ?//' |
  grep -v -F "${ESC}[36;1m" |
  sed "s/${ESC}\[[0-9;]*m//g" |
  grep -v '^##\[' |
  grep -E -- "$PATTERN" || true)
[[ -n $LINES ]] || { echo "run_evidence.sh: no line of run $RUN matches: $PATTERN" >&2; exit 1; }

echo "## $TITLE (run $RUN)"
echo '```'
printf '%s\n' "$LINES"
echo '```'
echo