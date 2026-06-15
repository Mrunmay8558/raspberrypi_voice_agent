# Future Options

This document tracks the next product and platform options for the Raspberry Pi
voice agent.

## Local Dashboard

Build and run a local FastAPI dashboard on the Raspberry Pi. The dashboard is
intended for users on the same WiFi/LAN as the Pi.

Initial scope:

- Login with a generated first-run password.
- Change the dashboard password from the UI.
- Show voice-agent service status.
- Scan and connect WiFi networks.
- Scan, pair, trust, connect, and disconnect Bluetooth devices.

The dashboard should not be exposed through a public Cloudflare quick tunnel by
default because it controls privileged device settings.

## Hermes Access

Hermes can remain available locally through the configured gateway port. Remote
access should later use a named Cloudflare Tunnel plus Cloudflare Access or
another strong authentication layer.

For now, the local dashboard should show the local URL users can open after they
join the same WiFi as the Pi.

## Remote Pipecat Client

For lower-resource devices, the wake listener can start a remote Daily client
instead of the local Pipecat bot. The device keeps wake-word detection local, then
requests a Daily room/token from the vaani_core public Daily endpoint and joins
as an audio-only client.

Current direction:

- `VOICE_RUNTIME_MODE=local` runs `python -m voice_bot.bot`
- `VOICE_RUNTIME_MODE=remote_daily` runs `python -m voice_client.runner`
- `EIGI_API_KEY` stays in `.env`
- template agent ID and `/v1/public/daily` URL live in `config.example.json`
- local device values live in ignored `config.json`
- per-device agent ID and `/v1/public/daily` URL live in `user.json` or are
  saved from the local dashboard
- `VOICE_CLIENT_TYPE=native` is the only supported remote client path

The native client uses the Pipecat C++ Daily transport with PortAudio. It is the
preferred path for lower-resource devices that should not depend on Chromium.

## Wake Word Options

Current implementation:

- `openWakeWord`
- Good for a fixed phrase such as `hey jarvis`
- Uses ONNX on Raspberry Pi

Future custom wake-word option:

- Vosk with constrained grammar
- Better if users need arbitrary wake phrases without training
- Needs a real Pi compatibility and false-trigger test before replacing
  `openWakeWord`

## Language, STT, And TTS

Future dashboard settings should include:

- STT language/provider
- TTS language/voice
- Assistant response language
- Multilingual mode controls

These are intentionally out of the first dashboard slice.
