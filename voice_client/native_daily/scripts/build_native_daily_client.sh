#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NATIVE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT_ROOT="$(cd "${NATIVE_DIR}/../.." && pwd)"
DEPS_DIR="${VOICE_NATIVE_DEPS_DIR:-${PROJECT_ROOT}/.native_deps}"
DEPS_DIR="$(mkdir -p "${DEPS_DIR}" && cd "${DEPS_DIR}" && pwd)"
BASE_SDK_DIR="${DEPS_DIR}/pipecat-client-cxx"
DAILY_SDK_DIR="${DEPS_DIR}/pipecat-client-cxx-daily"
BIN_DIR="${NATIVE_DIR}/bin"

if [[ -z "${DAILY_CORE_PATH:-}" ]]; then
  cat >&2 <<'EOF'
DAILY_CORE_PATH is required.

Download the Daily Core C++ SDK for your platform from:
  https://github.com/daily-co/daily-core-sdk/releases

Then run:
  export DAILY_CORE_PATH=/path/to/daily-core-sdk
EOF
  exit 1
fi

DAILY_CORE_PATH="$(cd "${DAILY_CORE_PATH}" && pwd)"

mkdir -p "${DEPS_DIR}" "${BIN_DIR}"

if [[ ! -d "${BASE_SDK_DIR}/.git" ]]; then
  git clone https://github.com/pipecat-ai/pipecat-client-cxx "${BASE_SDK_DIR}"
fi

if [[ ! -d "${DAILY_SDK_DIR}/.git" ]]; then
  git clone https://github.com/pipecat-ai/pipecat-client-cxx-daily "${DAILY_SDK_DIR}"
fi

# Daily Core SDK v0.20.0 renamed NativeDeviceManager to DailyDeviceManager.
# Keep the cloned client dependency buildable until upstream releases the same fix.
if grep -q "NativeDeviceManager" "${DAILY_SDK_DIR}/include/daily_transport.h"; then
  perl -0pi -e "s/NativeDeviceManager\\*/DailyDeviceManager*/g" \
    "${DAILY_SDK_DIR}/include/daily_transport.h"
fi

cmake "${BASE_SDK_DIR}" -G Ninja -B"${BASE_SDK_DIR}/build" -DCMAKE_BUILD_TYPE=Release
ninja -C "${BASE_SDK_DIR}/build"

export PIPECAT_SDK_PATH="${BASE_SDK_DIR}"
export DAILY_CORE_PATH

cmake "${DAILY_SDK_DIR}" -G Ninja -B"${DAILY_SDK_DIR}/build" -DCMAKE_BUILD_TYPE=Release
ninja -C "${DAILY_SDK_DIR}/build"

export DAILY_PIPECAT_SDK_PATH="${DAILY_SDK_DIR}"

EXAMPLE_DIR="${DAILY_SDK_DIR}/examples/c++-portaudio"
cmake "${EXAMPLE_DIR}" -G Ninja -B"${EXAMPLE_DIR}/build" -DCMAKE_BUILD_TYPE=Release
ninja -C "${EXAMPLE_DIR}/build"

cp "${EXAMPLE_DIR}/build/example_audio" "${BIN_DIR}/pipecat-daily-client"
chmod +x "${BIN_DIR}/pipecat-daily-client"

echo "Installed native Daily client at ${BIN_DIR}/pipecat-daily-client"
