# Voice Bot

This folder contains the fully local Raspberry Pi voice runtime.

## Responsibilities

- create the local Pipecat audio transport
- run Deepgram STT, OpenAI-compatible LLM calls, and Cartesia TTS
- manage idle prompts and clean session shutdown
- stop the pipeline when the LLM returns the private `__END_CALL__` sentinel

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
