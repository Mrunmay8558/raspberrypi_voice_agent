#!/usr/bin/env bash

set -euo pipefail

# Render the templated systemd units in `systemd/` with the current project
# path and runtime user, then install them into `/etc/systemd/system`.

usage() {
  cat <<'EOF'
Usage: sudo ./scripts/install_boot_services.sh [--enable-now] [--user USER] [--project-root PATH]

Installs the Raspberry Pi voice assistant systemd units with the current
project path and user rendered into the service files.
EOF
}

if [[ ${EUID} -ne 0 ]]; then
  echo "Run this script with sudo." >&2
  exit 1
fi

ENABLE_NOW=false
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_USER="${SUDO_USER:-}"

# Parse a small set of installation-time overrides so the same templates can
# be reused across machines without editing the unit files by hand.
while [[ $# -gt 0 ]]; do
  case "$1" in
    --enable-now)
      ENABLE_NOW=true
      shift
      ;;
    --user)
      RUN_USER="$2"
      shift 2
      ;;
    --project-root)
      PROJECT_ROOT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "${RUN_USER}" ]]; then
  RUN_USER="$(logname 2>/dev/null || true)"
fi

if [[ -z "${RUN_USER}" ]]; then
  echo "Unable to determine the non-root user. Pass --user explicitly." >&2
  exit 1
fi

# Resolve the concrete runtime identity that the services should use after
# installation.
RUN_GROUP="$(id -gn "${RUN_USER}")"
RUN_UID="$(id -u "${RUN_USER}")"
SYSTEMD_DIR="/etc/systemd/system"
PROJECT_ROOT="$(cd "${PROJECT_ROOT}" && pwd)"

# The wrapper scripts are referenced directly by systemd ExecStart lines.
chmod +x "${PROJECT_ROOT}/scripts/"*.sh

install_unit() {
  local source_file="$1"
  local target_file="${SYSTEMD_DIR}/$(basename "${source_file}")"

  # Replace placeholders in the committed templates with machine-specific
  # values before writing the final unit into the systemd directory.
  sed \
    -e "s|__PROJECT_ROOT__|${PROJECT_ROOT}|g" \
    -e "s|__RUN_USER__|${RUN_USER}|g" \
    -e "s|__RUN_GROUP__|${RUN_GROUP}|g" \
    -e "s|__RUN_UID__|${RUN_UID}|g" \
    "${source_file}" > "${target_file}"

  chmod 0644 "${target_file}"
  echo "Installed ${target_file}"
}

install_unit "${PROJECT_ROOT}/systemd/hermes-gateway.service"
install_unit "${PROJECT_ROOT}/systemd/cloudflared-hermes-tunnel.service"
install_unit "${PROJECT_ROOT}/systemd/dashboard.service"
install_unit "${PROJECT_ROOT}/systemd/voice-bot-wake.service"
install_unit "${PROJECT_ROOT}/systemd/voice-assistant-stack.target"

# Make systemd aware of the freshly installed units before optionally enabling
# the target that pulls the whole stack together.
systemctl daemon-reload

if [[ "${ENABLE_NOW}" == "true" ]]; then
  systemctl enable --now voice-assistant-stack.target
else
  echo "Installed units. Enable them with:"
  echo "  sudo systemctl enable --now voice-assistant-stack.target"
fi
