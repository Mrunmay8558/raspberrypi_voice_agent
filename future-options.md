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
