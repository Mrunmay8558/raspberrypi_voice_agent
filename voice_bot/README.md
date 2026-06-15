# Voice Bot

This folder contains the fully local Raspberry Pi voice runtime.

## Responsibilities

- create the local Pipecat audio transport
- run Deepgram STT, OpenAI-compatible LLM calls, and Cartesia TTS
- manage idle prompts and clean session shutdown
- stop the pipeline when the LLM returns the private `__END_CALL__` sentinel
- prevent local speaker audio from interrupting the bot's own speech

## Entry Point

Run the local bot directly with:

```bash
python -m voice_bot.bot
```

## Main Files

- `bot.py`: builds and runs the local Pipecat pipeline
- `__init__.py`: package marker

The wake listener does not live here anymore. The only wake-word runtime is
`wake_uplister.listener`.

## Local Speaker Echo

The local audio path does not provide acoustic echo cancellation by itself. To
avoid the bot treating its own speaker output as a user interruption, `bot.py`
mutes user frames while the bot is speaking and disables Pipecat interruption
frames for local turn-start detection.

This is intentional for Raspberry Pi speaker setups. It trades true barge-in
for stable playback. For hands-free full-duplex interruption, use an audio path
with real echo cancellation or a headset/earbuds where speaker output does not
enter the microphone.

## Acoustic Echo Cancellation

AEC has to happen in the OS audio layer or in the audio hardware. The local
Pipecat transport consumes microphone and speaker devices; it does not create
an echo-cancelled device by itself.

On Raspberry Pi OS with PipeWire/PulseAudio compatibility available, create an
echo-cancelled default source/sink with:

```bash
./scripts/setup_audio_aec.sh
```

Then enable interruption while the bot is speaking:

```bash
LOCAL_AUDIO_BARGE_IN=true
python -m voice_bot.bot
```

If the OS default devices are not the AEC devices, set explicit PyAudio indexes
in `.env` or `config.json`:

```bash
AUDIO_INPUT_DEVICE_INDEX=
AUDIO_OUTPUT_DEVICE_INDEX=
```

Leave `LOCAL_AUDIO_BARGE_IN=false` when using open speakers without AEC. That
mode is more reliable because it prevents speaker echo from cancelling the
assistant's own response.
