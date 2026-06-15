# Systemd Units

This directory contains the systemd templates used to boot the Raspberry Pi
voice assistant stack. These files are not installed directly. The script
`scripts/install_boot_services.sh` renders each template with the actual
project path, runtime user, group, and uid before copying it into
`/etc/systemd/system`.

## Unit Roles

`voice-assistant-stack.target`

- Top-level target for the whole stack.
- Pulls in the dashboard, Hermes gateway, Cloudflare tunnel, and wake listener.
- Use this target when enabling or starting the full system.

`dashboard.service`

- Starts the local FastAPI dashboard with `python -m dashboard.main`.
- Intended for setup and maintenance from the same LAN or WiFi network.
- Runs continuously and restarts automatically on failure.

`hermes-gateway.service`

- Starts the Hermes OpenAI-compatible gateway through
  `scripts/start_hermes_gateway.sh`.
- The wrapper script loads `.env`, resolves config defaults from `config.py`,
  and then launches the configured Hermes command.
- Other services can depend on this unit when they require the local gateway.

`cloudflared-hermes-tunnel.service`

- Starts a Cloudflare quick tunnel for the Hermes gateway through
  `scripts/start_cloudflared_tunnel.sh`.
- Waits until the local gateway port is reachable before launching
  `cloudflared`.
- Depends on `hermes-gateway.service` because it only makes sense once the
  local endpoint exists.

`voice-bot-wake.service`

- Runs the wake-word listener with `python -m wake_uplister.listener`.
- Uses the per-user `XDG_RUNTIME_DIR` and DBus session address so audio and
  Bluetooth integrations can resolve correctly under systemd.
- When the wake word is detected, the listener starts either the local voice
  bot or the remote Daily client, depending on `VOICE_RUNTIME_MODE`.

## Installation

Install or refresh the units with:

```bash
sudo ./scripts/install_boot_services.sh
```

Install and immediately enable the full stack with:

```bash
sudo ./scripts/install_boot_services.sh --enable-now
```

## Operations

Enable and start the full stack:

```bash
sudo systemctl enable --now voice-assistant-stack.target
```

Check status for the full stack or a single unit:

```bash
systemctl status voice-assistant-stack.target
systemctl status dashboard.service
```

Read recent logs:

```bash
journalctl -u voice-bot-wake.service -n 100 --no-pager
journalctl -u hermes-gateway.service -n 100 --no-pager
```
