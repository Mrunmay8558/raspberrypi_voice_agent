# Native Daily Client

This folder is for the no-browser remote voice client.

Runtime flow:

```text
wake_uplister.listener
-> python -m voice_client.runner
-> local broker at http://127.0.0.1:8090/api/start
-> native Pipecat C++ Daily client
-> Daily room returned by vaani_core /v1/public/daily
```

The native binary is expected at:

```text
voice_client/native_daily/bin/pipecat-daily-client
```

You can override that in `user.json`:

```json
{
  "voice_client": {
    "type": "native",
    "native_bin": "/usr/local/bin/pipecat-daily-client",
    "native_config_file": "voice_client/native_daily/config.json"
  }
}
```

## Raspberry Pi Setup

Install native build/audio dependencies:

```bash
sudo apt update
sudo apt install -y build-essential cmake ninja-build git libcurl4-openssl-dev libportaudio2 portaudio19-dev
```

Download the Daily Core C++ SDK for Linux `aarch64` from:

```text
https://github.com/daily-co/daily-core-sdk/releases
```

Extract it somewhere stable, for example:

```text
/opt/daily-core-sdk
```

Then build the native client:

```bash
export DAILY_CORE_PATH=/opt/daily-core-sdk
./voice_client/native_daily/scripts/build_native_daily_client.sh
```

The script builds:

- `pipecat-ai/pipecat-client-cxx`
- `pipecat-ai/pipecat-client-cxx-daily`
- the official PortAudio example binary

It then installs the example binary as:

```text
voice_client/native_daily/bin/pipecat-daily-client
```

## Configuration

Secrets stay in `.env`:

```bash
VOICE_RUNTIME_MODE=remote_daily
EIGI_API_KEY=your_public_api_key
```

Non-secret device/user config stays in `user.json`:

```json
{
  "remote_voice": {
    "daily_session_url": "http://localhost:4000/v1/public/daily",
    "agent_id": "6a23e90cdb48d202c0cd35c7",
    "conversation_metadata": {
      "agent_id": "6a23e90cdb48d202c0cd35c7"
    },
    "conversation_visibility": false,
    "conversation_config_type": "VOICE"
  },
  "voice_client": {
    "type": "native",
    "native_bin": "voice_client/native_daily/bin/pipecat-daily-client",
    "native_config_file": "voice_client/native_daily/config.json"
  }
}
```

## Browser Fallback

The browser implementation remains available for Raspberry Pi testing:

```json
{
  "voice_client": {
    "type": "browser"
  }
}
```

The production no-browser path should use `native`.
