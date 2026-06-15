# Wake Listener

This folder contains the always-on wake-word runtime.

## Responsibilities

- listen continuously on the configured microphone
- run openWakeWord detection locally
- avoid duplicate voice runtime launches with pid tracking
- start either the local voice bot or the remote Daily client based on
  `VOICE_RUNTIME_MODE`

## Entry Point

Run the wake listener with:

```bash
python -m wake_uplister.listener
```

## Main Files

- `listener.py`: microphone capture, wake detection, and runtime launch logic
- `config.py`: shared wake-listener config re-exports from the root `config.py`

The package name is currently `wake_uplister` because that is the name already
used across imports, docs, and systemd units in this repository.
