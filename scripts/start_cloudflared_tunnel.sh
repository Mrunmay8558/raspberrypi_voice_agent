#!/usr/bin/env bash

set -euo pipefail

# Start a Cloudflare quick tunnel only after the local gateway endpoint is
# reachable. This avoids publishing a dead URL while Hermes is still booting.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  . "${ENV_FILE}"
  set +a
fi

# Pull the final defaults from `config.py` so the shell wrapper stays aligned
# with the repository's single configuration source of truth.
eval "$({ \
  PYTHONPATH="${PROJECT_ROOT}" python3 - <<'PY'
from config import DEFAULT_CLOUDFLARED_BIN
from config import DEFAULT_CLOUDFLARED_QUICK_TUNNEL
from config import DEFAULT_CLOUDFLARED_TARGET_URL
from config import DEFAULT_CLOUDFLARED_WAIT_TIMEOUT_SECS

print(f"CONFIG_DEFAULT_CLOUDFLARED_BIN={DEFAULT_CLOUDFLARED_BIN!r}")
print(f"CONFIG_DEFAULT_CLOUDFLARED_WAIT_TIMEOUT_SECS={DEFAULT_CLOUDFLARED_WAIT_TIMEOUT_SECS!r}")
print(f"CONFIG_DEFAULT_CLOUDFLARED_QUICK_TUNNEL={DEFAULT_CLOUDFLARED_QUICK_TUNNEL!r}")
print(f"CONFIG_DEFAULT_CLOUDFLARED_TARGET_URL={DEFAULT_CLOUDFLARED_TARGET_URL!r}")
PY
})"

CLOUDFLARED_BIN="${CLOUDFLARED_BIN:-$CONFIG_DEFAULT_CLOUDFLARED_BIN}"
CLOUDFLARED_WAIT_TIMEOUT_SECS="${CLOUDFLARED_WAIT_TIMEOUT_SECS:-$CONFIG_DEFAULT_CLOUDFLARED_WAIT_TIMEOUT_SECS}"
CLOUDFLARED_QUICK_TUNNEL="${CLOUDFLARED_QUICK_TUNNEL:-$CONFIG_DEFAULT_CLOUDFLARED_QUICK_TUNNEL}"
CLOUDFLARED_TARGET_URL="${CLOUDFLARED_TARGET_URL:-$CONFIG_DEFAULT_CLOUDFLARED_TARGET_URL}"

if [[ "${CLOUDFLARED_QUICK_TUNNEL}" != "true" ]]; then
  echo "This setup uses Cloudflare quick tunnel by default. Set CLOUDFLARED_QUICK_TUNNEL=true or edit this script if you need another mode." >&2
  exit 1
fi

wait_url="${CLOUDFLARED_TARGET_URL#*://}"
wait_host_port="${wait_url%%/*}"
WAIT_HOST="${wait_host_port%%:*}"
WAIT_PORT="${wait_host_port##*:}"

if [[ "${WAIT_HOST}" == "${WAIT_PORT}" ]]; then
  WAIT_PORT=80
fi

wait_for_gateway() {
  local deadline=$((SECONDS + CLOUDFLARED_WAIT_TIMEOUT_SECS))

  # `/dev/tcp` gives us a dependency-free readiness check before starting the
  # long-running Cloudflare process.
  while ! (echo > "/dev/tcp/${WAIT_HOST}/${WAIT_PORT}") >/dev/null 2>&1; do
    if (( SECONDS >= deadline )); then
      echo "Timed out waiting for service on ${WAIT_HOST}:${WAIT_PORT}" >&2
      exit 1
    fi
    sleep 1
  done
}

wait_for_gateway

echo "Starting Cloudflare quick tunnel for ${CLOUDFLARED_TARGET_URL}"
exec "${CLOUDFLARED_BIN}" tunnel --url "${CLOUDFLARED_TARGET_URL}"
