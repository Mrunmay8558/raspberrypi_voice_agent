# Raspberry Pi Voice Agent

This repository runs a Raspberry Pi voice assistant stack with local wake-word
detection, a local setup dashboard, and two conversation runtime modes.

## What This Project Does

The device continuously listens for a wake word on the Raspberry Pi microphone.
When the wake word is detected, it starts one of two voice runtimes:

- `local`: run the full Pipecat voice bot directly on the Raspberry Pi
- `remote_daily`: keep wake-word detection local, then connect audio to a
  deployed Eigi voice bot through the native Pipecat Daily client

The repository also includes a local FastAPI dashboard for:

- service status
- WiFi scanning and connection
- Bluetooth scanning and connection
- dashboard password management
- remote voice client configuration

## Main Components

```text
raspberrypi_voice_agent/
├── config.py
├── env_store.py
├── dashboard/
├── scripts/
├── systemd/
├── voice_bot/
├── voice_client/
├── wake_uplister/
├── config.example.json
├── user.example.json
├── requirements.txt
└── README.md
```

Key runtime areas:

- `wake_uplister/`: wake-word listener using `openwakeword`
- `voice_bot/`: local Pipecat voice bot
- `voice_client/`: remote Daily session runner and local broker for the native
  C++ client
- `dashboard/`: local configuration dashboard
- `systemd/`: unit templates for boot-time startup
- `scripts/`: helper scripts used by systemd and installation

## Runtime Modes

### Local mode

In local mode, the wake listener starts:

```bash
python -m voice_bot.bot
```

This path uses:

- Deepgram STT
- Cartesia TTS
- an OpenAI-compatible Hermes endpoint
- local microphone and speaker audio on the Raspberry Pi

### Remote Daily mode

In remote mode, the wake listener starts:

```bash
python -m voice_client.runner
```

This path:

- detects the wake word locally on the device
- creates a Daily session through the Eigi public API
- starts a local FastAPI broker
- launches the native Pipecat Daily C++ audio client

This mode is intended for lower-resource hardware that should not run the full
voice bot locally.

## Configuration Model

Configuration is layered in this order:

1. `.env`
2. local ignored `config.json`
3. committed `config.example.json`

Additional local files:

- `user.json`: ignored per-device remote voice settings
- `user.example.json`: committed template for `user.json`
- `run/dashboard_auth.json`: generated dashboard credential store
- `run/bot.pid`: wake-listener pid tracking file

Do not commit:

- `.env`
- `config.json`
- `user.json`
- API keys
- Daily room URLs or tokens
- Cloudflare quick-tunnel URLs
- generated dashboard passwords

## Setup

### 1. Create the Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Create local config files

```bash
cp .env.example .env
cp config.example.json config.json
cp user.example.json user.json
```

### 3. Fill in local values

Typical values to configure:

- `DEEPGRAM_API_KEY`
- `CARTESIA_API_KEY`
- `EIGI_API_KEY` when using remote mode
- Hermes/OpenAI-compatible endpoint values if they differ from defaults
- agent id and remote session values in `user.json` for remote mode

`OPENAI_API_KEY` may remain blank when the local Hermes gateway does not enforce
auth. The local bot falls back to a placeholder value for OpenAI-compatible
requests.

## Common Commands

Activate the environment first:

```bash
source .venv/bin/activate
```

Run the local bot directly:

```bash
python -m voice_bot.bot
```

Run the wake listener:

```bash
python -m wake_uplister.listener
```

Run the remote Daily client directly:

```bash
python -m voice_client.runner
```

Run the local dashboard:

```bash
./start_dashboard.sh
```

Run the no-browser setup CLI:

```bash
python -m dashboard.cli status
python -m dashboard.cli wifi scan
python -m dashboard.cli bluetooth devices
```

## Dashboard

The dashboard is a local setup surface intended for devices on the same LAN or
WiFi as the Raspberry Pi. It is not intended for public exposure by default.

Start it manually:

```bash
./start_dashboard.sh
```

Then open:

```text
http://raspberrypi.local:8080
```

or:

```text
http://<pi-ip-address>:8080
```

On first run, the dashboard generates a username like `EIGIxxxxxx` and a
password, then logs both. Check:

```bash
journalctl -u dashboard.service -n 80 --no-pager
```

The dashboard currently supports:

- service status
- WiFi management through `nmcli`
- Bluetooth management through `bluetoothctl`
- remote voice settings
- dashboard password change

For hardware without a browser, use the CLI version of the same setup surface:

```bash
python -m dashboard.cli status
python -m dashboard.cli wifi scan
python -m dashboard.cli wifi connect "SSID_NAME"
python -m dashboard.cli bluetooth scan
python -m dashboard.cli bluetooth connect AA:BB:CC:DD:EE:FF
python -m dashboard.cli remote-voice show
python -m dashboard.cli api-keys show
```

Add `--json` before the command when another tool needs structured output:

```bash
python -m dashboard.cli --json status
```

## Wake Word

Wake-word detection runs through `openwakeword` in `wake_uplister/listener.py`.

Current defaults:

- wake word: `hey jarvis`
- sample rate: `16000`
- frame size: `1280`
- inference framework: `onnx`

Useful environment overrides:

- `WAKEWORD_MODEL`
- `WAKEWORD_THRESHOLD`
- `WAKEWORD_COOLDOWN_SECS`
- `WAKEWORD_VAD_THRESHOLD`
- `WAKEWORD_INFERENCE_FRAMEWORK`

If the voice runtime is already active, the wake listener will not launch a
second copy.

## Local Hermes Gateway

The local voice bot expects an OpenAI-compatible endpoint. By default it uses
the Hermes gateway on:

```text
http://127.0.0.1:8642/v1
```

When testing through a Cloudflare URL instead of localhost:

```bash
LOCAL_VOICE_TESTING=false
```

The Cloudflare OpenAI-compatible base URL is configured in local `config.json`.

## Native Daily Client

The remote mode uses the Pipecat C++ Daily client with PortAudio.

Build it with:

```bash
./voice_client/native_daily/scripts/build_native_daily_client.sh
```

You must provide the Daily Core SDK path first, typically through
`DAILY_CORE_PATH`, as described in:

- [voice_client/native_daily/README.md](voice_client/native_daily/README.md)
- [docs/pipecat-cpp-client-setup.md](docs/pipecat-cpp-client-setup.md)

## Boot Services

The repository includes systemd templates for:

- Hermes gateway
- Cloudflare tunnel
- dashboard
- wake listener
- top-level stack target

Install and enable the full stack:

```bash
sudo ./scripts/install_boot_services.sh --enable-now
```

For unit details, see:

- [systemd/README.md](systemd/README.md)

## Folder Guides

More focused runtime docs live in:

- [voice_bot/README.md](voice_bot/README.md)
- [voice_client/README.md](voice_client/README.md)
- [wake_uplister/README.md](wake_uplister/README.md)

Planned platform extensions and future work are tracked in:

- [future-options.md](future-options.md)

## Validation

Useful checks before pushing changes:

```bash
PYTHONPYCACHEPREFIX=/tmp/raspberrypi_voice_agent_pycache .venv/bin/python -m compileall \
  config.py env_store.py dashboard voice_bot voice_client wake_uplister
node --check dashboard/static/app.js
.venv/bin/python -m json.tool config.example.json >/dev/null
.venv/bin/python -m json.tool user.example.json >/dev/null
```
