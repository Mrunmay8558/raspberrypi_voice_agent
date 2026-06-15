# AGENTS.md

This file gives coding agents the working rules and repository context needed
to change this project safely.

## Purpose

This repository runs a Raspberry Pi voice assistant stack with two runtime
modes:

- `local`: run the Pipecat voice bot directly on the device.
- `remote_daily`: detect the wake word locally, then connect audio to a
  deployed Eigi voice bot through the native Pipecat Daily client.

The repository also includes a local FastAPI dashboard for WiFi, Bluetooth,
service health, remote-voice configuration, and dashboard authentication.

## Repo Layout

Primary application areas:

- `config.py`: central configuration loader. Reads `.env`, `config.json`, and
  `config.example.json`.
- `env_store.py`: reads and writes dashboard-managed secrets in `.env`.
- `wake_uplister/listener.py`: wake-word listener implementation.
- `voice_bot/bot.py`: local Pipecat voice bot entrypoint.
- `voice_client/runner.py`: remote-session runner that starts the local broker
  and native Daily client.
- `voice_client/server.py`: local FastAPI broker consumed by the native client.
- `voice_client/session.py`: creates Eigi Daily sessions.
- `voice_client/config_store.py`: loads and persists remote voice settings from
  `user.json` plus config defaults.
- `dashboard/core/apis`: FastAPI bootstrap, route modules, request/response
  schemas, and API dependencies.
- `dashboard/core/controllers`: business-logic layer for dashboard APIs.
- `dashboard/core/services`: host-specific operations such as `nmcli`,
  `bluetoothctl`, and `systemctl`.
- `dashboard/commons`: shared dashboard logger and auth/session helpers.
- `dashboard/static`: plain HTML/CSS/JS dashboard frontend.
- `systemd/`: service unit templates and stack targets.
- `scripts/`: operational helper scripts for Raspberry Pi setup.

Reference material that should usually not be edited unless explicitly asked:

- `FDE/`: reference/tutorial material.
- `pipecat/`: vendored upstream reference tree.

## Current Entry Points

Use these commands unless the user explicitly wants something else:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python -m voice_bot.bot
python -m wake_uplister.listener
python -m voice_client.runner
python -m dashboard.main
python -m dashboard.cli status
```

Native Daily client build:

```bash
./voice_client/native_daily/scripts/build_native_daily_client.sh
```

Dashboard service unit currently starts:

```bash
python -m dashboard.main
```

## Configuration Model

Config sources are layered in this order:

1. `.env`
2. local ignored `config.json`
3. committed `config.example.json`

Additional runtime config:

- `user.json`: ignored, device-specific remote voice settings.
- `user.example.json`: committed template for `user.json`.
- `run/dashboard_auth.json`: generated dashboard credential store.
- `run/bot.pid`: pid file used by the wake listener.

Never commit:

- `.env`
- `config.json`
- `user.json`
- generated dashboard passwords
- API keys
- Daily room URLs or tokens
- Cloudflare quick tunnel URLs
- real agent IDs tied to a user account unless the user explicitly asks

## Runtime Notes

Wake-word behavior:

- openWakeWord runs locally through `wake_uplister/listener.py`
- the listener starts either `voice_bot.bot` or `voice_client.runner`
- the choice is controlled by `VOICE_RUNTIME_MODE`

Local voice mode:

- uses Hermes/OpenAI-compatible endpoint configured through `config.py`
- `LOCAL_VOICE_TESTING` decides whether the OpenAI base URL resolves to local
  Hermes or a Cloudflare URL

Remote Daily mode:

- requires `EIGI_API_KEY` in `.env`
- requires remote voice settings in `user.json` or config defaults
- `voice_client/runner.py` starts `voice_client.server:app` and launches the
  native C++ Daily client

Dashboard structure:

- `dashboard/main.py` is the single Python entrypoint for both `app` and
  `main()`
- `dashboard/cli.py` is the no-browser setup interface and should reuse
  dashboard controllers instead of duplicating service logic
- FastAPI bootstrap lives in `dashboard/core/apis/api.py`
- auth/session dependency functions live in
  `dashboard/core/apis/dependencies.py`
- dashboard auth/session persistence lives in `dashboard/commons/auth.py`

## Editing Rules For This Repo

- Prefer existing structure over introducing another layer.
- Keep dashboard code inside `dashboard/core/apis`, `dashboard/core/controllers`,
  `dashboard/core/services`, and `dashboard/commons`.
- Keep route modules thin. Business logic belongs in controllers. Shell and
  host integration belongs in services.
- Public Python functions and non-trivial helpers should have type hints and
  real docstrings.
- Do not log secrets, tokens, or raw API keys.
- Preserve backward compatibility only when there is an active runtime consumer.
  Remove dead compatibility layers once the repo is fully migrated.
- Avoid editing `FDE/` and `pipecat/` unless the user explicitly asks.

## Validation

Run narrow checks relevant to the change. For most Python/dashboard/config
changes:

```bash
PYTHONPYCACHEPREFIX=/tmp/raspberrypi_voice_agent_pycache .venv/bin/python -m compileall \
  config.py env_store.py dashboard voice_bot voice_client wake_uplister
node --check dashboard/static/app.js
.venv/bin/python -m json.tool config.example.json >/dev/null
.venv/bin/python -m json.tool user.example.json >/dev/null
```

For dashboard-only edits, at minimum:

```bash
PYTHONPYCACHEPREFIX=/tmp/raspberrypi_voice_agent_pycache .venv/bin/python -m compileall dashboard
```

For remote voice changes, also verify:

```bash
python -m voice_client.runner
```

Only do that when the native binary, local broker port, and Eigi config are
actually available in the current environment.
