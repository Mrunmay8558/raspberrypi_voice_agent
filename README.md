# Raspberry Pi Daily Voice Bot

Minimal Pipecat Daily transport bot for Raspberry Pi 5.

This bot uses:

- Deepgram STT with `nova-2` in multilingual mode
- Cartesia TTS with the voice `71a7ad14-091c-4e8e-a314-022ece01c121`
- A local OpenAI-compatible endpoint at `http://127.0.0.1:8642/v1`

## Project structure

```text
raspberrypi_voice_agent/
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
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
python voice_bot/bot.py
```

The bot is pinned to the local OpenAI-compatible gateway on port `8642`, so no remote OpenAI base URL is used.

If your gateway expects a different model name, set `OPENAI_MODEL` before starting the bot.