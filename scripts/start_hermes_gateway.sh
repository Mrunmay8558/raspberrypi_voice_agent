#!/usr/bin/env bash

set -euo pipefail

# Load environment overrides, resolve config-backed defaults, and then hand off
# to the configured Hermes gateway command.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  . "${ENV_FILE}"
  set +a
fi

# Read config values through Python instead of duplicating default logic in
# bash. This keeps the service wrapper and application config in sync.
eval "$({ \
  PYTHONPATH="${PROJECT_ROOT}" python3 - <<'PY'
from config import DEFAULT_HERMES_GATEWAY_COMMAND
from config import DEFAULT_HERMES_HOST
from config import DEFAULT_HERMES_PORT

print(f"CONFIG_DEFAULT_HERMES_GATEWAY_COMMAND={DEFAULT_HERMES_GATEWAY_COMMAND!r}")
print(f"CONFIG_DEFAULT_HERMES_HOST={DEFAULT_HERMES_HOST!r}")
print(f"CONFIG_DEFAULT_HERMES_PORT={DEFAULT_HERMES_PORT!r}")
PY
})"

HERMES_GATEWAY_COMMAND="${HERMES_GATEWAY_COMMAND:-$CONFIG_DEFAULT_HERMES_GATEWAY_COMMAND}"

export HERMES_GATEWAY_HOST="${HERMES_GATEWAY_HOST:-$CONFIG_DEFAULT_HERMES_HOST}"
export HERMES_GATEWAY_PORT="${HERMES_GATEWAY_PORT:-$CONFIG_DEFAULT_HERMES_PORT}"

# Execute through a login shell so user-installed CLIs and shell startup env
# remain available when systemd starts the gateway.
cd "${PROJECT_ROOT}"
echo "Starting Hermes gateway on ${HERMES_GATEWAY_HOST}:${HERMES_GATEWAY_PORT}"
exec /bin/bash -lc "${HERMES_GATEWAY_COMMAND}"
