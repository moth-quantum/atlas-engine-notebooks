#!/usr/bin/env bash
# Create and manage Moth notebooks from the command line. Needs curl, jq and MOTH_API_KEY; MOTH_API_BASE
# points at another API.
#
#   scripts/notebook.sh create <git-url> [ref] [path]   create from a public repo and wait until ready
#   scripts/notebook.sh status <id>                     phase, readiness and why it is not ready
#   scripts/notebook.sh wait <id>                       poll until ready (or failed)
#   scripts/notebook.sh list                            your notebooks
#   scripts/notebook.sh stop <id>                       shut the server down; the workspace is kept
#   scripts/notebook.sh delete <id>                     delete the notebook and its workspace
#
# Example:
#   scripts/notebook.sh create https://github.com/moth-quantum/atlas-engine-notebooks.git main blur/blur_notebook.py
set -euo pipefail

API="${MOTH_API_BASE:-https://api.mothquantum.com}/api/v1/notebooks"

usage() { sed -n '2,13s/^# \{0,1\}//p' "$0"; exit "${1:-0}"; }

call() {  # call METHOD URL [JSON]: prints the response body; on an HTTP error prints it to stderr and fails
  local auth="Authorization: Bearer ${MOTH_API_KEY:?set MOTH_API_KEY (Atlas → API keys)}" out
  if ! out=$(curl -sS --fail-with-body -X "$1" "$2" -H "$auth" ${3:+-H "Content-Type: application/json" -d "$3"}); then
    echo "notebook.sh: $1 $2 failed${out:+: $out}" >&2
    return 1
  fi
  printf '%s\n' "$out"
}

show() { jq -r '"\(.id)  \(.phase)\(if .ready then " · ready" else "" end)\(if (.queue_position // 0) > 0 then " · queue \(.queue_position)" else "" end)\(if .message then " · \(.message)" else "" end)  \(.display_name // "")"'; }

wait_ready() {
  local nb last=""
  while :; do
    nb=$(call GET "$API/$1")
    [[ "$(show <<<"$nb")" != "$last" ]] && { last=$(show <<<"$nb"); echo "$last"; }
    [[ $(jq -r .ready <<<"$nb") == true ]] && return 0
    [[ $(jq -r .phase <<<"$nb") == Failed ]] && return 1
    sleep 5
  done
}

for arg in "$@"; do [[ "$arg" == -h || "$arg" == --help ]] && usage; done

case "${1:-}" in
  create)
    [[ -n "${2:-}" ]] || usage 1
    [[ "$2" == https://* ]] || { echo "notebook.sh: <git-url> must be a public https:// clone URL, got '$2'" >&2; exit 1; }
    body=$(jq -n --arg url "$2" --arg ref "${3:-}" --arg path "${4:-}" '{
      display_name: ((if $path != "" then $path else $url end) | split("/") | last | .[:100]),
      source: {git: ({url: $url} + (if $ref != "" then {ref: $ref} else {} end) + (if $path != "" then {path: $path} else {} end))}
    }')
    id=$(call POST "$API" "$body" | jq -r .id)
    echo "created $id"
    wait_ready "$id" ;;
  status) [[ -n "${2:-}" ]] || usage 1; call GET "$API/$2" | show ;;
  wait)   [[ -n "${2:-}" ]] || usage 1; wait_ready "$2" ;;
  list)   call GET "$API" | jq -c '.notebooks[]' | while read -r nb; do show <<<"$nb"; done ;;
  stop)   [[ -n "${2:-}" ]] || usage 1; call POST "$API/$2/stop" | show ;;
  delete) [[ -n "${2:-}" ]] || usage 1; call DELETE "$API/$2" >/dev/null && echo "deleted $2" ;;
  help|-h|--help) usage ;;
  *) usage 1 ;;
esac
