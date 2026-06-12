#!/usr/bin/env bash

set -euo pipefail

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

RUN_GROUP="$(id -gn "${RUN_USER}")"
SYSTEMD_DIR="/etc/systemd/system"
PROJECT_ROOT="$(cd "${PROJECT_ROOT}" && pwd)"

chmod +x "${PROJECT_ROOT}/scripts/"*.sh

install_unit() {
  local source_file="$1"
  local target_file="${SYSTEMD_DIR}/$(basename "${source_file}")"

  sed \
    -e "s|__PROJECT_ROOT__|${PROJECT_ROOT}|g" \
    -e "s|__RUN_USER__|${RUN_USER}|g" \
    -e "s|__RUN_GROUP__|${RUN_GROUP}|g" \
    "${source_file}" > "${target_file}"

  chmod 0644 "${target_file}"
  echo "Installed ${target_file}"
}

install_unit "${PROJECT_ROOT}/systemd/hermes-gateway.service"
install_unit "${PROJECT_ROOT}/systemd/cloudflared-hermes-tunnel.service"
install_unit "${PROJECT_ROOT}/systemd/voice-bot-wake.service"
install_unit "${PROJECT_ROOT}/systemd/voice-assistant-stack.target"

systemctl daemon-reload

if [[ "${ENABLE_NOW}" == "true" ]]; then
  systemctl enable --now voice-assistant-stack.target
else
  echo "Installed units. Enable them with:"
  echo "  sudo systemctl enable --now voice-assistant-stack.target"
fi