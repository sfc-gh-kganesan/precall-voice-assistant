#!/bin/bash
set -euo pipefail

# p67-health-check.sh — SessionStart hook for CoCo profile.
# Runs on every CoCo session start; must complete in <10 seconds.

PREFIX="[P67]"

# ── 1. Check p67 is in PATH ────────────────────────────────────────────────
if ! command -v p67 &>/dev/null; then
  echo "${PREFIX} p67 CLI not found. Install from the GH release or run the install script."
  exit 0
fi

# ── 2. Check at least one connection exists ─────────────────────────────────
conn_output=$(p67 connection list 2>&1) || true

if echo "${conn_output}" | grep -q "No connections configured"; then
  echo "${PREFIX} No p67 connection configured. Run: p67 connection add <name> --endpoint <url>"
  exit 0
fi

# ── 3. If a default connection exists, probe its health endpoint ────────────
# p67 connection list marks the default with "* <name>" and prints
# "Endpoint: <url>" on the next line.
default_endpoint=""
found_default=false
while IFS= read -r line; do
  if [[ "${found_default}" == "true" ]]; then
    # Next line after "* name" should be "  Endpoint: <url>"
    if [[ "${line}" =~ ^[[:space:]]*Endpoint:[[:space:]]*(.*) ]]; then
      default_endpoint="${BASH_REMATCH[1]}"
    fi
    break
  fi
  if [[ "${line}" =~ ^\*[[:space:]] ]]; then
    found_default=true
  fi
done <<< "${conn_output}"

if [[ -z "${default_endpoint}" ]]; then
  # No default connection — just note p67 is available
  echo "${PREFIX} Ready. No default connection set."
  exit 0
fi

# Probe the health endpoint (5-second timeout, silent on network errors)
if ! curl -sf "${default_endpoint}/api/health" --max-time 5 >/dev/null 2>&1; then
  echo "${PREFIX} Controld not reachable at ${default_endpoint}. The service may be down."
  exit 0
fi

echo "${PREFIX} Ready. CLI connected to ${default_endpoint}."
