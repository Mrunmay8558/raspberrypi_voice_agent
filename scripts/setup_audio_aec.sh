#!/usr/bin/env bash
# Create a PipeWire/PulseAudio echo-cancelled source/sink for local voice use.
#
# This script loads PulseAudio's WebRTC echo-cancel module through `pactl`.
# On Raspberry Pi OS setups using PipeWire's PulseAudio compatibility layer,
# this gives the bot an OS-level AEC device without changing Pipecat code.
#
# Usage:
#   ./scripts/setup_audio_aec.sh
#
# Optional overrides:
#   AEC_SOURCE_MASTER=<source-name> ./scripts/setup_audio_aec.sh
#   AEC_SINK_MASTER=<sink-name> ./scripts/setup_audio_aec.sh
#
# Leave AUDIO_INPUT_DEVICE_INDEX/AUDIO_OUTPUT_DEVICE_INDEX empty when this
# script successfully sets the AEC source/sink as the OS defaults.

set -euo pipefail

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_command pactl

SOURCE_MASTER="${AEC_SOURCE_MASTER:-@DEFAULT_SOURCE@}"
SINK_MASTER="${AEC_SINK_MASTER:-@DEFAULT_SINK@}"
SOURCE_NAME="${AEC_SOURCE_NAME:-voice_agent_aec_source}"
SINK_NAME="${AEC_SINK_NAME:-voice_agent_aec_sink}"

echo "Loading WebRTC echo cancellation module..."
echo "  source_master=${SOURCE_MASTER}"
echo "  sink_master=${SINK_MASTER}"
echo "  source_name=${SOURCE_NAME}"
echo "  sink_name=${SINK_NAME}"

if pactl list short sources | awk '{print $2}' | grep -Fxq "${SOURCE_NAME}" &&
  pactl list short sinks | awk '{print $2}' | grep -Fxq "${SINK_NAME}"; then
  echo "AEC source/sink already exist. Setting them as defaults."
  pactl set-default-source "${SOURCE_NAME}"
  pactl set-default-sink "${SINK_NAME}"
  exit 0
fi

MODULE_ID="$(
  pactl load-module module-echo-cancel \
    source_name="${SOURCE_NAME}" \
    sink_name="${SINK_NAME}" \
    source_master="${SOURCE_MASTER}" \
    sink_master="${SINK_MASTER}" \
    aec_method=webrtc \
    use_master_format=1 \
    source_properties=device.description="Voice Agent AEC Source" \
    sink_properties=device.description="Voice Agent AEC Sink"
)"

pactl set-default-source "${SOURCE_NAME}"
pactl set-default-sink "${SINK_NAME}"

echo "AEC module loaded: ${MODULE_ID}"
echo
echo "Default source:"
pactl get-default-source
echo
echo "Default sink:"
pactl get-default-sink
echo
echo "Available sources:"
pactl list short sources
echo
echo "Available sinks:"
pactl list short sinks
