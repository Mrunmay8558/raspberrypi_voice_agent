# Raspberry Pi Local Voice Bot

Minimal Pipecat local-audio voice bot for Raspberry Pi 5.

This bot uses:

- Deepgram STT with `nova-2` in multilingual mode
- Cartesia TTS with the voice `71a7ad14-091c-4e8e-a314-022ece01c121`
- A local OpenAI-compatible endpoint at `http://127.0.0.1:8642/v1`

## Project structure

```text
raspberrypi_voice_agent/
├── cloudflared/
├── config.py
├── .env.example
├── .gitignore
├── dashboard/
├── README.md
├── requirements.txt
├── scripts/
├── systemd/
├── wake_uplister/
└── voice_bot/
    ├── __init__.py
    └── bot.py
```

## Setup

```bash
cd raspberrypi_voice_agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in the API keys in `.env`.

`OPENAI_API_KEY` can stay blank if your local gateway does not enforce auth. The bot falls back to a local placeholder key for the OpenAI-compatible client.

## Run

```bash
cd raspberrypi_voice_agent
source .venv/bin/activate
python -m voice_bot.bot
```

By default, the bot uses the local OpenAI-compatible Hermes gateway on
`http://127.0.0.1:8642/v1`.

Set this in `.env` when testing through the Cloudflare tunnel instead:

```bash
LOCAL_VOICE_TESTING=false
```

The Cloudflare URL itself still lives in `config.py`:

```python
CLOUDFLARE_OPENAI_BASE_URL = "https://your-tunnel.trycloudflare.com/v1"
```

Set `LOCAL_VOICE_TESTING=true` to switch back to localhost.

If your gateway expects a different model name, set `OPENAI_MODEL` before starting the bot.

## Local setup dashboard

The repository includes a local FastAPI dashboard for Raspberry Pi setup and
maintenance. It is intended for users connected to the same WiFi/LAN as the Pi,
not for public internet exposure.

Start it manually:

```bash
cd raspberrypi_voice_agent
source .venv/bin/activate
uvicorn dashboard.main:app --host 0.0.0.0 --port 8080
```

or with the configured `DASHBOARD_HOST` and `DASHBOARD_PORT` values:

```bash
python -m dashboard.server
```

Open it from the same network:

```text
http://raspberrypi.local:8080
```

or:

```text
http://<pi-ip-address>:8080
```

On first run, the dashboard creates a generated admin password and logs it. Check:

```bash
journalctl -u dashboard.service -n 80 --no-pager
```

The dashboard currently supports:

- service status
- WiFi scanning and connection through `nmcli`
- Bluetooth scanning, pairing, trusting, connecting, and disconnecting through `bluetoothctl`
- dashboard password change

The password hash is stored in `run/dashboard_auth.json` by default. The plain
password is not stored.

The bot has two separate idle controls:

- `--user-idle-timeout-secs`: silence during a conversation before the bot asks whether you are still there
- `--pipeline-idle-timeout-secs`: worker-level cleanup timeout when the pipeline itself is idle

After repeated user-idle prompts, the bot speaks a short closing message and ends cleanly. The wake listener can then start a fresh bot session on the next wake word.

## Wake word listener for Raspberry Pi 5

The repository includes a separate wake listener that continuously listens on the Raspberry Pi microphone and starts the local voice bot when a wake word is detected.

### Install additional audio dependencies on Raspberry Pi

```bash
sudo apt update
sudo apt install -y libportaudio2 portaudio19-dev pipewire-alsa
```

Then install the Python packages:

```bash
cd raspberrypi_voice_agent
source .venv/bin/activate
pip install -r requirements.txt
```

The wake listener defaults to the ONNX inference backend because Raspberry Pi Python 3.13 does not have a reliable upstream TFLite runtime wheel for this setup. `openwakeword` includes ONNX support on Linux through its Python dependencies.

### Start the wake listener manually

```bash
cd raspberrypi_voice_agent
source .venv/bin/activate
python -m wake_uplister.listener
```

The listener opens the selected input device at its native sample rate and resamples to 16 kHz for wake-word detection. It feeds openWakeWord 80 ms frames, which is `1280` samples at 16 kHz.

By default, the listener watches for the `hey jarvis` wake word and launches:

```bash
python -m voice_bot.bot
```

The bot uses the Raspberry Pi's default PipeWire audio devices, so paired
AirPods or any configured default microphone/speaker can be used directly
without opening a browser UI.

Those default Python-side values now live in `config.py`.

If the bot is already running, the listener will not start a second copy.

### Wake listener environment settings

The default values come from `config.py`. If you want to override them without editing code, set these values in `.env`:

- `WAKEWORD_MODEL`: pretrained model name such as `hey jarvis`, `alexa`, or a custom model path
- `WAKEWORD_THRESHOLD`: minimum score required to trigger the bot
- `WAKEWORD_COOLDOWN_SECS`: cooldown after a trigger before another trigger is allowed
- `WAKEWORD_VAD_THRESHOLD`: speech activity threshold to reduce false positives
- `WAKEWORD_INFERENCE_FRAMEWORK`: `onnx` by default for this Raspberry Pi setup, or `tflite` if a compatible runtime is installed

### Start the wake listener on boot with systemd

Use the installer script so the systemd units are rendered with your actual project path and Raspberry Pi user:

```bash
sudo ./scripts/install_boot_services.sh --enable-now
```

If you only want the wake listener service enabled, you can still enable it by itself after installation:

```bash
sudo systemctl enable --now voice-bot-wake.service
```

## Boot stack for reboot recovery

The repository now includes a boot stack that can start all required local services after a Raspberry Pi reboot:

- Hermes gateway service on the local port used by the bot
- Cloudflare tunnel service that waits until the Hermes port is reachable
- Wake listener service that keeps listening for the wake word

### Configure the Hermes gateway command

The startup script reads its default Hermes settings from `config.py`. By default it uses `hermes gateway run --replace` and expects the gateway on `http://127.0.0.1:8642/v1`.

If you want to override that without editing code, you can still set:

```bash
HERMES_GATEWAY_COMMAND="hermes gateway run --replace"
```

If that command serves on a port other than `8642`, either change `HERMES_GATEWAY_PORT` to match it and update the bot, or keep the gateway configured to serve on `8642` so the bot can still reach `http://127.0.0.1:8642/v1`.

### Configure the Cloudflare tunnel

This setup now uses the direct quick-tunnel form by default:

```bash
cloudflared tunnel --url http://localhost:8642
```

The boot script runs that same pattern automatically. By default it targets `http://localhost:8642`.

The startup script reads its default Cloudflare settings from `config.py`. By default it uses:

```bash
cloudflared tunnel --url http://localhost:8642
```

If you want a different quick-tunnel target, you can still override it in `.env`:

```bash
CLOUDFLARED_TARGET_URL=http://localhost:8642
```

If you do not set `CLOUDFLARED_TARGET_URL`, the script uses `http://localhost:8642` directly.

### Install and enable the full reboot stack

```bash
cd raspberrypi_voice_agent
sudo ./scripts/install_boot_services.sh --enable-now
```

That installs these units:

- `dashboard.service`
- `hermes-gateway.service`
- `cloudflared-hermes-tunnel.service`
- `voice-bot-wake.service`
- `voice-assistant-stack.target`

### Control the stack

```bash
sudo systemctl restart voice-assistant-stack.target
sudo systemctl status dashboard.service
sudo systemctl status hermes-gateway.service
sudo systemctl status cloudflared-hermes-tunnel.service
sudo systemctl status voice-bot-wake.service
```

### Check logs

```bash
journalctl -u dashboard.service -f
journalctl -u hermes-gateway.service -f
journalctl -u cloudflared-hermes-tunnel.service -f
journalctl -u voice-bot-wake.service -f
```
