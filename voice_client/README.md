# Voice Client

This folder contains the remote voice runtime used on lower-resource devices.

## Responsibilities

- load remote session configuration from `user.json`, config defaults, and `.env`
- create an Eigi Daily session through the public API
- start a local FastAPI broker for the native client
- launch the native Pipecat Daily C++ audio client

## Entry Point

Run the remote client flow with:

```bash
python -m voice_client.runner
```

## Main Files

- `runner.py`: starts the broker and launches the native client
- `server.py`: local FastAPI broker consumed by the native client
- `session.py`: creates and normalizes Eigi Daily sessions
- `config_store.py`: loads and persists remote voice settings
- `native_daily/`: native client binary, config, and build script
