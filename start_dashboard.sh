#!/usr/bin/env bash
# Start the local FastAPI dashboard from the repository root.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_ROOT}"

if [[ -x ".venv/bin/python" ]]; then
  exec .venv/bin/python -m dashboard.main
fi

exec python -m dashboard.main
