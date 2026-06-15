# Pipecat C++ Client Setup Guide

This guide installs the native Pipecat Daily C++ client on a Raspberry Pi and
connects it to the `remote_daily` runtime in this repository.

Use this guide when:

- the device should keep wake-word detection local
- the actual voice bot runs remotely on Eigi
- the device should not open a browser for audio

## What This Setup Does

Runtime flow:

```text
wake_uplister.listener
-> python -m voice_client.runner
-> local broker at http://127.0.0.1:8090/api/start
-> native Pipecat Daily C++ client
-> Daily room returned by the Eigi public API
```

Expected native binary after build:

```text
voice_client/native_daily/bin/pipecat-daily-client
```

## Prerequisites

Before starting, make sure the Raspberry Pi has:

- Raspberry Pi OS / Debian with network access
- this repository cloned locally
- Python virtual environment already created for the repo
- a valid `EIGI_API_KEY`
- a valid Eigi `agent_id`

You also need the Daily Core C++ SDK for Linux `aarch64`:

```text
https://github.com/daily-co/daily-core-sdk/releases
```

## Step 1: Check Network Health

If `apt` is slow or keeps hanging, check the network before installing
packages:

```bash
ping -c 4 8.8.8.8
ping -c 4 deb.debian.org
ping -c 4 archive.raspberrypi.com
```

If package downloads are still slow, try IPv4-only installs:

```bash
sudo apt-get -o Acquire::ForceIPv4=true install -y cmake libcurl4-openssl-dev
```

If DNS looks broken, check:

```bash
resolvectl status
cat /etc/resolv.conf
```

In practice, Ethernet is the cleanest fix when mirrors are unstable over Wi-Fi.

## Step 2: Install System Packages

Install the native build and audio dependencies:

```bash
sudo apt-get update
sudo apt-get install -y \
  build-essential \
  cmake \
  ninja-build \
  git \
  libcurl4-openssl-dev \
  libportaudio2 \
  portaudio19-dev
```

You can verify the important tools with:

```bash
which cmake
which ninja
which git
dpkg -s libcurl4-openssl-dev libportaudio2 portaudio19-dev | grep '^Status:'
```

## Step 3: Download the Daily Core SDK

Download the Linux `aarch64` Daily Core SDK from the Daily releases page and
extract it somewhere stable.

Recommended location:

```text
/opt/daily-core-sdk
```

Example:

```bash
sudo mkdir -p /opt/daily-core-sdk
sudo tar -xzf daily-core-sdk-linux-aarch64.tar.gz -C /opt/daily-core-sdk --strip-components=1
```

Verify the directory exists:

```bash
ls -la /opt/daily-core-sdk
```

## Step 4: Configure Environment and User Settings

From the project root:

```bash
cd ~/Documents/raspberrypi_voice_agent
cp -n .env.example .env
cp -n config.example.json config.json
cp -n user.example.json user.json
```

### Required `.env` values

Add the Eigi API key:

```bash
EIGI_API_KEY=your_eigi_public_api_key
```

### Required `config.json` values

Switch runtime mode:

```json
{
  "runtime": {
    "voice_runtime_mode": "remote_daily"
  }
}
```

For production Eigi:

```json
{
  "remote_voice": {
    "public_api_base_url": "https://api.eigi.ai/v1/public",
    "daily_session_url": "https://api.eigi.ai/v1/public/daily"
  }
}
```

### Required `user.json` values

Set the target remote agent:

```json
{
  "remote_voice": {
    "agent_id": "your-agent-id",
    "conversation_metadata": {
      "agent_id": "your-agent-id"
    },
    "conversation_visibility": false,
    "conversation_config_type": "VOICE",
    "dynamic_variables": {},
    "is_test_call": false
  },
  "voice_client": {
    "type": "native",
    "native_bin": "voice_client/native_daily/bin/pipecat-daily-client",
    "native_config_file": "voice_client/native_daily/config.json"
  }
}
```

`agent_id` should always be present inside `conversation_metadata`.

## Step 5: Build the Native Pipecat Client

Set the Daily SDK path:

```bash
export DAILY_CORE_PATH=/opt/daily-core-sdk
```

Run the build script:

```bash
./voice_client/native_daily/scripts/build_native_daily_client.sh
```

This script:

- clones `pipecat-ai/pipecat-client-cxx`
- clones `pipecat-ai/pipecat-client-cxx-daily`
- builds both native dependencies
- builds the PortAudio example client
- installs it as `voice_client/native_daily/bin/pipecat-daily-client`

## Step 6: Verify the Native Binary

Check that the binary exists:

```bash
ls -l voice_client/native_daily/bin/pipecat-daily-client
```

Optional sanity check:

```bash
file voice_client/native_daily/bin/pipecat-daily-client
```

## Step 7: Test the Remote Runtime Manually

Activate the Python environment:

```bash
source .venv/bin/activate
```

Run the remote client path directly:

```bash
python -m voice_client.runner
```

If configuration is correct, this flow should:

- create an Eigi Daily session
- start the local broker on `127.0.0.1:8090`
- launch the native C++ client

## Step 8: Use the Wake Listener With Remote Runtime

When `config.json` is set to:

```json
{
  "runtime": {
    "voice_runtime_mode": "remote_daily"
  }
}
```

the wake listener will launch the remote client path instead of the local bot.

Manual test:

```bash
python -m wake_uplister.listener
```

Systemd test:

```bash
sudo systemctl restart voice-bot-wake.service
sudo systemctl status voice-bot-wake.service --no-pager -n 50
journalctl -u voice-bot-wake.service -n 100 --no-pager
```

## Useful Validation Commands

Check JSON files:

```bash
.venv/bin/python -m json.tool config.json >/dev/null
.venv/bin/python -m json.tool user.json >/dev/null
```

Check Python imports:

```bash
PYTHONPYCACHEPREFIX=/tmp/raspberrypi_voice_agent_pycache \
  .venv/bin/python -m compileall config.py env_store.py voice_client wake_uplister
```

## Common Problems

### 1. `DAILY_CORE_PATH is required`

Set it before building:

```bash
export DAILY_CORE_PATH=/opt/daily-core-sdk
```

### 2. `pipecat-daily-client` binary is missing

The native build did not complete. Re-run:

```bash
./voice_client/native_daily/scripts/build_native_daily_client.sh
```

### 3. `apt` is hanging

Try IPv4-only:

```bash
sudo apt-get -o Acquire::ForceIPv4=true install -y cmake libcurl4-openssl-dev
```

If it still hangs, use Ethernet or a better Wi-Fi connection.

### 4. Wake listener still starts the local bot

Check `config.json`:

```json
{
  "runtime": {
    "voice_runtime_mode": "remote_daily"
  }
}
```

Then restart:

```bash
sudo systemctl restart voice-bot-wake.service
```

## Quick Command List

If you already have the SDK tarball and a working network, this is the shortest
setup path:

```bash
cd ~/Documents/raspberrypi_voice_agent
sudo apt-get update
sudo apt-get install -y build-essential cmake ninja-build git libcurl4-openssl-dev libportaudio2 portaudio19-dev
cp -n .env.example .env
cp -n config.example.json config.json
cp -n user.example.json user.json
export DAILY_CORE_PATH=/opt/daily-core-sdk
./voice_client/native_daily/scripts/build_native_daily_client.sh
source .venv/bin/activate
python -m voice_client.runner
```
