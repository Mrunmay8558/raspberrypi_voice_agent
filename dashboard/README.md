# Dashboard

The dashboard is the local setup and operations surface for the Raspberry Pi
voice agent. It gives a browser UI and a no-browser CLI for configuring the
device after the repo is installed on hardware.

## What It Does

The dashboard helps manage:

- service status for the voice-agent stack
- WiFi scanning and connection
- Bluetooth scanning, pairing, trusting, connecting, and disconnecting
- Eigi remote voice settings
- API keys stored in the local `.env`
- dashboard login password

It is intended for local network setup. Do not expose it directly to the public
internet without adding a proper external access layer.

## Folder Layout

```text
dashboard/
├── main.py
├── cli.py
├── commons/
├── core/
│   ├── apis/
│   ├── controllers/
│   └── services/
└── static/
```

- `main.py`: FastAPI/Uvicorn entrypoint for the browser dashboard.
- `cli.py`: command-line setup tool for devices without a browser.
- `commons/`: shared logging and authentication helpers.
- `core/apis/`: FastAPI routers, request schemas, and response schemas.
- `core/controllers/`: application-level request handling.
- `core/services/`: OS command wrappers for WiFi, Bluetooth, and system state.
- `static/`: HTML, CSS, and JavaScript for the browser UI.

## Required Setup

From the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp config.example.json config.json
cp user.example.json user.json
```

Fill the required keys in `.env`:

```env
EIGI_API_KEY=
OPENAI_API_KEY=
DEEPGRAM_API_KEY=
CARTESIA_API_KEY=
```

`config.json`, `user.json`, `.env`, and `run/dashboard_auth.json` are local
machine files and should stay uncommitted.

## Run Manually

Start the browser dashboard:

```bash
./start_dashboard.sh
```

The script runs `.venv/bin/python` when the local virtual environment exists.
Otherwise it falls back to `python -m dashboard.main`.

Open it from a device on the same network:

```text
http://<pi-ip-address>:8080
```

The default host and port come from `config.json`:

```json
{
  "dashboard": {
    "host": "0.0.0.0",
    "port": 8080
  }
}
```

You can override them in `.env`:

```env
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8080
```

## Install As A Boot Service

Install all voice-agent systemd units, including the dashboard:

```bash
sudo ./scripts/install_boot_services.sh --enable-now
```

Install for a specific Linux user:

```bash
sudo ./scripts/install_boot_services.sh --enable-now --user eigi
```

Check status:

```bash
systemctl status dashboard.service
```

View logs:

```bash
journalctl -u dashboard.service -n 100 --no-pager
```

Restart only the dashboard:

```bash
sudo systemctl restart dashboard.service
```

## Login

On first run, the dashboard creates a local credential store at:

```text
run/dashboard_auth.json
```

By default, the first-run username is generated in this format:

```text
EIGIxxxxxx
```

The generated username and password are printed in the dashboard logs:

```bash
journalctl -u dashboard.service -n 100 --no-pager
```

After logging in, the password can be changed from the dashboard UI.

## CLI For Headless Devices

Use the CLI when the hardware has no browser:

```bash
python -m dashboard.cli --help
```

Common commands:

```bash
python -m dashboard.cli status
python -m dashboard.cli wifi scan
python -m dashboard.cli wifi connect "SSID_NAME"
python -m dashboard.cli bluetooth devices
python -m dashboard.cli bluetooth scan
python -m dashboard.cli bluetooth connect AA:BB:CC:DD:EE:FF
python -m dashboard.cli remote-voice show
python -m dashboard.cli api-keys show
```

For machine-readable output:

```bash
python -m dashboard.cli --json status
```

## Remote Voice Configuration

The dashboard can switch the device between:

- `local`: run `voice_bot.bot` locally on the Raspberry Pi.
- `remote_daily`: run `voice_client.runner` and connect to a deployed Eigi bot.

Remote settings are written to local config files and can include:

- public API base URL
- Daily session URL
- agent id
- conversation metadata
- dynamic variables
- native Daily client path

## Notes

- WiFi commands require `nmcli`.
- Bluetooth commands require `bluetoothctl`.
- Service commands require systemd.
- Some operations may require the service user to have the correct OS
  permissions for NetworkManager, Bluetooth, and audio devices.
