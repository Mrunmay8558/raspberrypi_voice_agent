# Building "Buddy" — A Raspberry Pi 5 Voice Companion

### A Complete Technical Walkthrough, From Bare Board to Talking Agent

---

This document is the full, detailed record of how we turned a bare Raspberry Pi 5
into **Buddy**, an always-on voice companion. It is written so that someone who
did not sit through the build — a partner, a teammate, a future version of
yourself — can understand not just *what* we did, but *why* each decision was
made, *how* each component works internally, and *what went wrong* and how we
fixed it.

Every component's source code is included verbatim and explained. Every command
is given. Every dead end we hit is documented, because the dead ends are often
where the real learning lives.

**What Buddy is, in one sentence:** a Raspberry Pi running a local Nous Hermes AI
agent, exposed over an OpenAI-compatible API, spoken to through a Pipecat voice
pipeline, woken by a custom wake word, and configured from a web browser.

---

## Table of Contents

1. [The Goal and the Final Architecture](#1-the-goal-and-the-final-architecture)
2. [Understanding the Raspberry Pi 5](#2-understanding-the-raspberry-pi-5)
3. [Flashing the Operating System](#3-flashing-the-operating-system)
4. [First Boot, SSH, and the Wi-Fi Country-Code Saga](#4-first-boot-ssh-and-the-wi-fi-country-code-saga)
5. [Lite vs Desktop: Switching the OS](#5-lite-vs-desktop-switching-the-os)
6. [The Brain: Installing the Nous Hermes Agent](#6-the-brain-installing-the-nous-hermes-agent)
7. [The Voice Pipeline: Pipecat](#7-the-voice-pipeline-pipecat)
8. [Audio Engineering on the Pi](#8-audio-engineering-on-the-pi)
9. [The Wake Word: Full Implementation](#9-the-wake-word-full-implementation)
10. [The Shared Config Store](#10-the-shared-config-store)
11. [The FastAPI Configuration Server](#11-the-fastapi-configuration-server)
12. [Wi-Fi Management from the Browser](#12-wi-fi-management-from-the-browser)
13. [Bluetooth Management from the Browser](#13-bluetooth-management-from-the-browser)
14. [Telegram Integration](#14-telegram-integration)
15. [Remote Access, Autonomy, and Security](#15-remote-access-autonomy-and-security)
16. [Packaging Everything as a Reusable Skill](#16-packaging-everything-as-a-reusable-skill)
17. [Appendix A: The Gotchas, Collected](#appendix-a-the-gotchas-collected)
18. [Appendix B: Complete Command Reference](#appendix-b-complete-command-reference)
19. [Appendix C: Full File Tree and Deployment](#appendix-c-full-file-tree-and-deployment)

---

## 1. The Goal and the Final Architecture

The brief was simple to state and rich to build: **run a Hermes agent locally on
a Raspberry Pi 5, expose it via an OpenAI-compatible API, and connect it to a
Pipecat voice bot so the device becomes a companion that talks back.** Aman was
new to Raspberry Pi, so the whole build was done from first principles, verifying
each step before moving to the next.

By the end, the system looked like this:

```
                          ┌─────────────────────────────────────────┐
                          │           Raspberry Pi 5 (8GB)           │
                          │                                          │
   🎤 mic ───────────────►│  Pipecat bot.py                          │
                          │   ├─ LocalAudioTransport.input()         │
                          │   ├─ Deepgram STT  (speech → text)       │
                          │   ├─ user aggregator → LLM context       │
                          │   ├─ OpenAILLMService ──────────┐        │
                          │   │     points at localhost:8642 │        │
                          │   │                              ▼        │
                          │   │            Nous Hermes agent (gateway)│
                          │   │            OpenAI-compatible API      │
                          │   │            /v1/chat/completions :8642 │
                          │   │                              │        │
                          │   ├─ Cartesia TTS  (text → speech)◄───────┘
                          │   └─ LocalAudioTransport.output()────────►│ 🔊 speaker
                          │                                          │
   "hey buddy" ──────────►│  wake_listener.py (Vosk)                 │
                          │   └─ launches bot.py per trigger         │
                          │                                          │
   🌐 browser ───────────►│  config_server (FastAPI :8080)           │
                          │   ├─ wake word / system prompt / idle    │
                          │   ├─ Wi-Fi  (nmcli)                      │
                          │   └─ Bluetooth (bluetoothctl)            │
                          │                                          │
   📱 Telegram ──────────►│  hermes gateway (Telegram adapter)       │
                          └─────────────────────────────────────────┘
```

Three processes run on the Pi: the **Hermes gateway** (the brain + Telegram + the
API server), the **wake listener** (which spawns the voice bot on demand), and
the **config server** (the web UI). They coordinate through one shared JSON file.

The crucial architectural insight that makes everything compose: **Hermes exposes
an OpenAI-compatible API.** Because Pipecat already speaks the OpenAI protocol, we
can point its LLM service at the local Hermes endpoint and Pipecat is none the
wiser — it thinks it's talking to OpenAI. This is why the voice layer and the
agent layer are completely decoupled and independently swappable.

---

## 2. Understanding the Raspberry Pi 5

Before touching software, it helps to understand what this device actually is,
because the mental model drives everything else.

### It is a complete computer

A Raspberry Pi is not a gadget or a microcontroller like an Arduino. It is a
full computer — same category as the MacBook used to set it up, just smaller and
ARM-based. It has a CPU, GPU, RAM, networking, and USB, and it runs a real
operating system (Raspberry Pi OS, a Debian Linux derivative). Everything you
know about Linux servers applies directly: `ssh`, `apt`, `python`, `systemd`,
file permissions, all of it.

The differences from a laptop: it is ARM architecture (not x86), it has no
built-in storage (the OS lives on a microSD card you insert underneath), no
battery, and no screen.

### The chips that matter

Two chips do essentially all the work, and everything else on the board is
connectors:

- **BCM2712** — the System-on-Chip, the "brain." Four ARM Cortex-A76 cores at
  2.4 GHz plus a GPU. This is what runs your code and, critically for a voice
  assistant, what generates tokens and processes audio.
- **RP1** — a dedicated I/O controller chip that drives all the ports and the
  GPIO pins. When you read a sensor or push audio over USB, RP1 is handling it.

### The ports and headers

- **40-pin GPIO header** — the thing a Pi has that laptops don't. Raw pins you
  wire directly to hardware: microphones, speakers, LEDs, sensors, or "HAT"
  add-on boards. This is what makes a Pi suitable for building a physical device.
- **2× USB 3.0 (blue)** and **2× USB 2.0** — keyboard, USB mic, USB speaker, or
  storage. We later attach a USB audio device here.
- **Gigabit Ethernet** — wired networking, an instant fallback when Wi-Fi misbehaves.
- **2× micro-HDMI** — note *micro*, not full-size; you need an adapter. Drives monitors.
- **USB-C** — power input only (5V/5A).
- **PCIe connector** — add a fast NVMe SSD via an M.2 HAT for quick model loading.
- **microSD slot (underside)** — where the OS lives.
- **Onboard Wi-Fi + Bluetooth** — wireless networking and wireless audio.

### RAM and why 8GB matters

The RAM is LPDDR4X, soldered to the board (not upgradable — you choose the
capacity at purchase). Run `free -h` after boot to confirm how much you have. For
this project the 8GB model gives comfortable headroom; if you were running a
*local* LLM (we did not — Hermes uses a cloud provider), the RAM would directly
determine which quantized model sizes fit.

### Power and cooling — not optional

Use the **official 27W USB-C supply (5V/5A)**. A phone charger may boot the Pi
but causes voltage throttling and flaky USB behavior, which matters the moment
you push the CPU or attach USB audio. For any sustained load, add the official
**active cooler** (a small fan + heatsink, about $5); the Pi 5 thermally throttles
without it.

### The operating mental model

You do **not** plug the Pi into your laptop like a peripheral. Both machines join
the same network, and you remote into the Pi over SSH. This is called running
**headless** — no monitor, no keyboard attached to the Pi. The way to think about
it: **your Mac is the cockpit, the Pi is the engine.** You write code, read logs,
and issue commands from the Mac's terminal; the Pi executes. This is exactly how
nearly all servers are operated, and Buddy is, at heart, a tiny personal server.

---

## 3. Flashing the Operating System

"Flashing" means writing the operating system image onto the microSD card so the
Pi can boot from it. We used the official **Raspberry Pi Imager** application on
the Mac.

### The steps, in order

1. **Insert the microSD** into the Mac (via a built-in slot or a USB reader).
2. Open Raspberry Pi Imager.
3. **Choose Device → Raspberry Pi 5.** This tailors the image to the board.
4. **Choose OS.** The first time, we picked **Raspberry Pi OS Lite (64-bit)**,
   found under the "Raspberry Pi OS (other)" submenu. "Lite" means no graphical
   desktop — just the command line. (More on this choice below.)
5. **Choose Storage → the microSD card.** A stern warning appears: writing
   **erases everything** on the card. Confirm the correct device is selected.
6. **OS customisation** — this is the single most important screen for a headless
   setup, because it pre-configures the things you'd otherwise have no way to set
   without a monitor and keyboard:
   - **Hostname:** `buddy`. This is the name the Pi announces on the network, so
     you can later reach it as `buddy.local`.
   - **Username and password:** username `aman`; Aman typed the password himself.
     (As a rule, you enter your own passwords — they should not pass through
     anyone or anything else.)
   - **Wi-Fi SSID and password:** the network name and password the Pi should
     join on first boot. The SSID must be typed *exactly* — a single wrong
     character causes a silent failure that looks identical to many other
     problems.
   - **Wi-Fi country / localisation:** the regulatory region. **This is the field
     that caused us the most trouble** (see the next section). It must match where
     you actually are.
   - **Enable SSH:** with **password authentication**. This is the switch that
     makes headless operation possible — without it, you cannot log in remotely.
7. **Write and verify.** The Imager writes the image (~5–10 minutes including the
   verify pass) and then **auto-ejects** the card.

### Why this customisation screen is the whole game

On a headless device, you have no opportunity to type a Wi-Fi password or enable
SSH after the fact — there's no screen to do it on. The customisation screen bakes
all of that into the image before first boot. Get it right and the Pi appears on
your network ready to SSH into. Get one field wrong and you're debugging blind.

---

## 4. First Boot, SSH, and the Wi-Fi Country-Code Saga

This is the part of the build that consumed the most time, and the lesson is
valuable enough that it deserves the full story rather than a one-line summary.

### What should happen

Insert the flashed card into the Pi, plug in USB-C power (no monitor needed),
wait ~2 minutes. On first boot the Pi resizes its filesystem to fill the card,
reboots once, and joins Wi-Fi. Then from the Mac:

```bash
ssh aman@buddy.local
```

You accept the host-key prompt by typing `yes`, enter your password, and you're
inside a Linux machine.

### What actually happened

The SSH command hung indefinitely. So did `ping`:

```bash
ping -c 3 buddy.local
# ping: cannot resolve buddy.local: Unknown host
```

"Unknown host" means the name `buddy.local` resolved to nothing — the Pi was not
announcing itself on the network. Two possibilities: the Pi wasn't booting, or it
booted but never joined Wi-Fi.

We attached a monitor to one of the micro-HDMI ports to look directly. The
console showed the Pi *had* booted fine:

```
Debian GNU/Linux 13 buddy tty1
My IP address is 127.0.0.1 ::ffff:127.0.0.1
buddy login:
```

That line — `My IP address is 127.0.0.1` — was the key clue. `127.0.0.1` is the
**loopback address**, the interface a machine uses to talk to itself. It means the
Pi had **no real network connection at all**. Wi-Fi had not connected.

### Diagnosing the radio

Logged in at the console, we ran `nmcli` (NetworkManager's command-line tool,
which manages connections on modern Raspberry Pi OS):

```
wlan0: unavailable
  "Broadcom Wi-Fi"
  wifi (brcmfmac), 88:A2:9E:B1:64:30, sw disabled, hw, mtu 1500
```

The decisive words: **`sw disabled`**. The Wi-Fi radio was **software-blocked** —
a state called "rfkill." The hardware was fine (`hw`), but software had switched
the radio off.

### Why the radio was blocked: the regulatory domain

Wi-Fi radios are legally required to operate only on the channels and power levels
permitted in their physical region. To enforce this, Linux keeps a **regulatory
domain** — a country code — and the Wi-Fi driver refuses to enable the radio until
it knows which country's rules to follow. If the country code is unset or wrong,
the safest thing the driver can do is keep the radio off. That is exactly the
`sw disabled` state.

The root cause traced back to the Imager's localisation step: the capital-city
selection had been left on a default (Abu Dhabi / UAE) that didn't match reality,
so the wrong (or effectively unusable) country code was baked in.

### The fix

```bash
sudo raspi-config nonint do_wifi_country IN   # set the Wi-Fi country to India
sudo rfkill unblock wifi                        # lift the software block
nmcli radio wifi on                             # turn the radio on
nmcli dev wifi list                             # the network is now visible
```

`raspi-config nonint do_wifi_country IN` is the non-interactive way to set the
regulatory domain (use your own country's code — `US`, `GB`, etc.).
`rfkill unblock wifi` clears the software kill-switch. After this the radio came
alive and the scan listed nearby networks.

### The takeaway

> **The Wi-Fi country code set in Raspberry Pi Imager is the number-one cause of
> "my headless Pi won't appear on the network." Set it correctly when flashing,
> and if you're ever staring at `127.0.0.1` and `sw disabled`, this is almost
> certainly why.**

This same regulatory-domain issue came back to bite us *again* much later when
scanning for networks from the web UI (Section 12) — proof that it pays to
understand a root cause rather than just paper over a symptom.

### A second, related lesson: mDNS is flaky

Even once Wi-Fi worked, `buddy.local` (which relies on a protocol called mDNS to
turn the hostname into an IP) was unreliable on this network — many routers and
client machines block or mishandle device-to-device mDNS discovery. The fix was
simply to use the Pi's IP address directly, which we found from the router's
connected-devices list:

```bash
ssh aman@192.168.1.10
```

From that point on we used the IP everywhere. It is consistently more reliable
than `.local`.

---

## 5. Lite vs Desktop: Switching the OS

After the Wi-Fi fix, Aman reconsidered the OS choice and asked whether the GUI
(desktop) version would be better, given the Pi has 8GB of RAM.

### The reasoning we worked through

The honest engineering answer for a *headless voice companion* is that **Lite is
the better default**, and 8GB of RAM is part of *why*, not a reason against it:

- A desktop environment permanently consumes roughly 700MB–1GB of RAM and a
  continuous slice of CPU just to render a screen — a screen that, on a companion
  device sitting on a desk with no monitor, **nobody ever looks at**.
- On a Pi, the CPU is precisely what does the useful work (audio processing, and
  if you ran one, model inference). Every cycle the desktop spends drawing a
  wallpaper is a cycle stolen from responsiveness.
- The desktop also runs its own audio stack, which can **fight the voice pipeline
  over the microphone and speaker** — a real source of bugs for exactly this kind
  of project.

The mental model: the device's true interface is a microphone and a speaker, not
a monitor. A desktop on a headless box is furniture in a house nobody lives in.

Crucially, the choice is **not** permanent in either direction, but the costs are
asymmetric: starting from Lite, you can add a full desktop later with a single
command (`sudo apt install raspberrypi-ui-mods`) and lose nothing. Starting from
Desktop and stripping it out cleanly is much messier.

### The decision and the re-flash

Despite the reasoning, Aman decided he wanted the desktop after all — a
legitimate preference, especially while learning, since having a screen to fall
back on is reassuring. So we re-flashed the same card with **Raspberry Pi OS
(64-bit) Desktop**, and this time set localisation correctly to **New Delhi /
India** (fixing the country-code problem at the source) and reset the keyboard
layout to `us` (the capital-city picker had auto-switched it to `in`).

After this boot, with the country code correct from the start, Wi-Fi connected on
its own and SSH worked immediately:

```bash
ssh aman@192.168.1.10
# Linux buddy 6.12.75+rpt-rpi-2712 ... aarch64
```

We were finally, reliably, inside the Pi.

---

## 6. The Brain: Installing the Nous Hermes Agent

With a working, networked Pi, we installed the component that does the thinking.

### What Hermes is, and why we used the real thing

There was an early ambiguity worth flagging: "Hermes agent" could mean a
hand-written harness, but what Aman wanted was the actual **Nous Research
hermes-agent** — an open-source, self-improving AI agent with persistent memory,
a skill system, and a built-in toolset (terminal, file operations, web search,
browser automation). Critically for us, it ships an **OpenAI-compatible API
server**, which is the seam that lets the voice pipeline plug into it cleanly.

Using the real agent (rather than a thin LLM wrapper we'd write ourselves) means
Buddy isn't just a chatbot — it's an agent that can actually *do* things: run
commands, search the web, remember across sessions.

### Installation

The one-line installer handles all dependencies itself — Python, Node.js,
ripgrep, ffmpeg — so the only prerequisite is `git`:

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
source ~/.bashrc
```

It installs to `~/.hermes/`, with the code under `~/.hermes/hermes-agent`, config
at `~/.hermes/config.yaml`, secrets at `~/.hermes/.env`, and a global `hermes`
command on the PATH.

### Choosing a model provider

Hermes needs an LLM provider behind it. The options included a Nous Portal
subscription (`hermes setup --portal`, one login for 300+ models plus their tool
gateway) or a direct provider key (`hermes model` to pick OpenAI, OpenRouter,
etc.). Aman configured it through a **Codex / ChatGPT subscription login**, which
Hermes supports as a provider, selecting a GPT-5.5-class model.

> **A note on latency we flagged at the time:** a large reasoning model is slow to
> produce its first token, and in a *voice* interaction that delay is felt
> directly — you say something and wait several seconds before Buddy starts
> talking. For snappier conversation, a smaller/faster model (changeable anytime
> with `hermes model`) is preferable. We left the choice to Aman, noting the
> tradeoff.

### Enabling the OpenAI-compatible API server

This is the step that turns Hermes from a CLI tool into a backend the voice bot
can call. Two environment lines enable it:

```bash
cat >> ~/.hermes/.env <<'EOF'
API_SERVER_ENABLED=true
API_SERVER_KEY=change-me-local-dev
EOF
hermes gateway
```

`hermes gateway` starts the long-running process that hosts the API server (and
also any messaging adapters like Telegram). On startup it prints:

```
[API Server] API server listening on http://127.0.0.1:8642
```

That terminal must stay running — it *is* Buddy's brain. The `API_SERVER_KEY` is
a bearer token; any client calling the API must present it.

### Verifying the brain before building on it

We never wire a new component to an unverified one. First a health check:

```bash
curl http://localhost:8642/health
# {"status": "ok", "platform": "hermes-agent", "version": "0.16.0"}
```

Then an actual completion through the OpenAI-compatible endpoint:

```bash
curl http://localhost:8642/v1/chat/completions \
  -H "Authorization: Bearer change-me-local-dev" \
  -H "Content-Type: application/json" \
  -d '{"model":"hermes-agent","messages":[{"role":"user","content":"Hello! Who are you?"}]}'
```

The response came back as proper OpenAI-shaped JSON:

```json
{
  "id": "chatcmpl-652f7e90...",
  "object": "chat.completion",
  "model": "hermes-agent",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content":
      "Hello! I'm Hermes Agent, an AI assistant by Nous Research. I can help with
       research, coding, files, web tasks, automation, scheduling, and using tools
       when needed to get real results rather than just advice."},
    "finish_reason": "stop"
  }],
  "usage": {"prompt_tokens": 12894, "completion_tokens": 76, "total_tokens": 12970}
}
```

The brain was alive. Note the endpoint shape that everything downstream relies on:
base URL `http://127.0.0.1:8642/v1`, model name `hermes-agent`, bearer
authentication. (Note also the ~13k prompt tokens even for "hello" — that's the
agent's substantial system prompt and tool definitions. It's why the agent is
capable, and part of why it's not instantaneous.)

### The dashboard

Hermes ships a local web dashboard (sessions, token usage and cost per model,
scheduled jobs, metrics, logs). It binds to localhost only:

```bash
hermes dashboard                 # serves on http://127.0.0.1:9119
```

To view it from the Mac safely, an SSH tunnel forwards the port without exposing
anything to the network:

```bash
ssh -L 9119:localhost:9119 aman@192.168.1.10
# then open http://localhost:9119 in the Mac browser
```

Raw logs live at `~/.hermes/logs/`, and `hermes doctor` runs diagnostics.

---

## 7. The Voice Pipeline: Pipecat

With a working brain, we built Buddy's ears and mouth using **Pipecat**, an
open-source Python framework for real-time voice agents. Pipecat's model is a
**pipeline** of processors that audio and text frames flow through.

### The conceptual pipeline

```
mic → speech-to-text → [add user turn to context] → LLM → text-to-speech → speaker
```

Each stage is a processor. Audio enters as raw frames from the microphone, gets
transcribed to text, the text is added to the conversation context, the LLM (our
local Hermes) produces a reply, that reply is synthesized to speech, and the
audio is played out the speaker. A **Voice Activity Detector (VAD)** decides when
you've finished speaking so the bot knows when to respond.

### Researching the current API first

Before writing a line, we checked the live Pipecat documentation and source,
because the framework's API had changed meaningfully from older examples. The
current shape uses `LocalAudioTransport` for the mic/speaker, `PipelineWorker` +
`WorkerRunner` to run the pipeline, `LLMContext` with `LLMContextAggregatorPair`
to manage conversation state, and `SileroVADAnalyzer` for turn detection. Writing
against stale examples would have produced code that simply doesn't import.

### The provider choice, and the failure that drove it

The very first version used OpenAI for *everything* — speech-to-text (Whisper)
and text-to-speech as well as being the LLM-protocol target. When we ran it, the
logs filled with errors on every single turn:

```
ERROR  OpenAISTTService#0 error: Unknown error occurred
DEBUG  OpenAISTTService#0 TTFB: 8.768s
DEBUG  OpenAISTTService#0 TTFB: 10.341s
```

Two problems: the OpenAI speech services were erroring outright, and even when
they worked their **time-to-first-byte was 8–10 seconds** — unusable for
conversation. (A subtlety worth noting: a ChatGPT/Codex *subscription* does not
cover the *API* audio endpoints, which need separately-billed API access — a
common source of confusion.)

So we switched to streaming-first specialist services:

- **Speech-to-text: Deepgram** — streaming transcription, very low latency.
- **Text-to-speech: Cartesia** — streaming synthesis, natural voices.
- **LLM: the local Hermes agent** (unchanged).

Streaming services begin returning results as the audio/words arrive, rather than
waiting for the whole request, which is exactly what conversation needs. This is
also Pipecat's own reference stack, which is a good signal.

### The complete `bot.py`, explained

Here is the full, final voice bot. After the listing, every significant part is
explained.

```python
"""Buddy's voice — the Pipecat pipeline.

mic → Deepgram STT → Hermes (local, OpenAI-compatible) → Cartesia TTS → speaker

Run directly for an always-on session, or let wake_listener.py launch it per
wake word. Either way it self-exits after BOT_IDLE_TIMEOUT seconds of silence
so the wake listener can resume.
"""

import asyncio
import os
import signal
import sys
import time

from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.local.audio import (
    LocalAudioTransport,
    LocalAudioTransportParams,
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_store import load_config  # noqa: E402

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")

HERMES_URL = os.getenv("HERMES_URL", "http://127.0.0.1:8642/v1")
HERMES_API_KEY = os.getenv("HERMES_API_KEY", "change-me-local-dev")

# User-tunable settings (set via the config web UI), read fresh each launch.
_CFG = load_config()
SYSTEM_PROMPT = _CFG["system_prompt"]
IDLE_TIMEOUT = float(_CFG["idle_timeout"])

# Frame types that count as "activity" (user or bot talking). Imported
# defensively so a renamed/missing class in some Pipecat version can't crash
# the bot — any that resolve are used to reset the idle timer.
_ACTIVITY_FRAMES = []
for _name in (
    "UserStartedSpeakingFrame",
    "UserStoppedSpeakingFrame",
    "TranscriptionFrame",
    "InterimTranscriptionFrame",
    "TTSStartedFrame",
    "TTSAudioRawFrame",
    "BotStartedSpeakingFrame",
    "BotStoppedSpeakingFrame",
):
    try:
        _mod = __import__("pipecat.frames.frames", fromlist=[_name])
        _ACTIVITY_FRAMES.append(getattr(_mod, _name))
    except (ImportError, AttributeError):
        pass
_ACTIVITY_FRAMES = tuple(_ACTIVITY_FRAMES)


class IdleMonitor(FrameProcessor):
    """Stamps the shared state whenever speech (user or bot) flows through."""

    def __init__(self, state: dict):
        super().__init__()
        self._state = state

    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)
        if _ACTIVITY_FRAMES and isinstance(frame, _ACTIVITY_FRAMES):
            self._state["last"] = time.monotonic()
        await self.push_frame(frame, direction)


async def _idle_watchdog(state: dict):
    """End the session after IDLE_TIMEOUT seconds without activity."""
    while True:
        await asyncio.sleep(1)
        if time.monotonic() - state["last"] > IDLE_TIMEOUT:
            logger.info(f"Idle for {IDLE_TIMEOUT:.0f}s — ending session.")
            # Same graceful path as Ctrl+C, which the runner handles cleanly.
            os.kill(os.getpid(), signal.SIGINT)
            return


async def main():
    state = {"last": time.monotonic()}

    transport = LocalAudioTransport(
        LocalAudioTransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        )
    )

    # Ears: Deepgram streaming transcription.
    stt = DeepgramSTTService(api_key=os.environ["DEEPGRAM_API_KEY"])

    # Voice: Cartesia TTS (default: "British Reading Lady" — swap via CARTESIA_VOICE).
    tts = CartesiaTTSService(
        api_key=os.environ["CARTESIA_API_KEY"],
        settings=CartesiaTTSService.Settings(
            voice=os.getenv("CARTESIA_VOICE", "71a7ad14-091c-4e8e-a314-022ece01c121"),
        ),
    )

    # Brain: the Nous Hermes agent running locally on this Pi via its
    # OpenAI-compatible API server. Pipecat believes it's OpenAI.
    llm = OpenAILLMService(
        api_key=HERMES_API_KEY,
        base_url=HERMES_URL,
        settings=OpenAILLMService.Settings(
            model="hermes-agent",
            system_instruction=SYSTEM_PROMPT,
        ),
    )

    context = LLMContext()
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
    )

    pipeline = Pipeline(
        [
            transport.input(),       # mic
            stt,                     # speech → text
            user_aggregator,         # add user turn to context
            llm,                     # Hermes
            tts,                     # text → speech
            IdleMonitor(state),      # reset idle timer on any speech
            transport.output(),      # speaker
            assistant_aggregator,    # add Buddy's reply to context
        ]
    )

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    context.add_message(
        {"role": "developer", "content": "Greet Aman briefly and naturally."}
    )
    await worker.queue_frames([LLMRunFrame()])

    from pipecat.workers.runner import WorkerRunner

    runner = WorkerRunner()
    await runner.add_workers(worker)

    asyncio.create_task(_idle_watchdog(state))
    await runner.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
```

**The imports and config block.** We pull in Pipecat's transport, services,
pipeline, and context classes. The `sys.path.insert` line lets `bot.py` (which
lives in `~/buddy/bot/`) import the shared `config_store` module that lives one
directory up in `~/buddy/`. `load_dotenv(override=True)` reads secrets from the
`.env` file. The system prompt and idle timeout are read from the shared config
store *at launch* — which matters because the wake listener relaunches `bot.py`
for every conversation, so any config change the user made in the web UI is
picked up on the next wake without restarting anything.

**The transport.** `LocalAudioTransport` is the Pipecat component that reads the
microphone and writes the speaker using the system's default audio devices via
PyAudio. We enable both input and output. Because we route audio through PipeWire
(see Section 8), the "default device" lands on whatever the user has connected —
Bluetooth earbuds, in our case — with no device-index juggling needed.

**The three services.** `DeepgramSTTService` transcribes; `CartesiaTTSService`
synthesizes (with a configurable voice ID); and `OpenAILLMService` is the LLM
stage — but note `base_url=HERMES_URL` and `api_key=HERMES_API_KEY`. This is the
linchpin: we use Pipecat's *OpenAI* service class but point it at our *local
Hermes* server. The `system_instruction` is Buddy's personality, which the Hermes
API server layers *on top of* its own core agent prompt (adding personality
without stripping the agent's tools).

**Context aggregation.** `LLMContext` holds the running conversation.
`LLMContextAggregatorPair` produces two processors — one that adds the user's
transcribed turn to the context before the LLM runs, and one that adds the bot's
spoken reply afterward — so the conversation has memory across turns. The user
aggregator is given the `SileroVADAnalyzer`, a small neural voice-activity
detector that decides when you've stopped talking.

**The pipeline order.** Frames flow top to bottom: mic → STT → user aggregator →
LLM → TTS → IdleMonitor → speaker → assistant aggregator. The `IdleMonitor`
(explained with the wake word, since that's its purpose) sits just before the
speaker so it observes both the user's transcription frames and the bot's speech
frames passing through.

**Kicking off the greeting.** We seed the context with a developer instruction to
greet Aman and queue an `LLMRunFrame`, so Buddy speaks first when a session
starts rather than waiting silently.

**The runner.** `PipelineWorker` wraps the pipeline with metrics; `WorkerRunner`
runs it. The `_idle_watchdog` task (Section 9) is what makes the bot exit after
silence. `runner.run()` blocks until the pipeline ends.

### The "Connection error" we had to fix

When first run with the new services, the bot transcribed perfectly (Deepgram
working) and Cartesia connected, but every turn failed at the LLM step:

```
ERROR  OpenAILLMService#0 exception ... Error during completion: Connection error.
```

A "Connection error" here is not authentication — it's the bot being unable to
*reach* the Hermes API at all. Two causes, both of which we checked:

1. **The gateway wasn't running.** `hermes gateway` must be alive in its own
   terminal. A quick `curl http://127.0.0.1:8642/health` confirms.
2. **The API key mismatch.** The bot's `HERMES_API_KEY` (in `~/buddy/.env`) must
   exactly equal the gateway's `API_SERVER_KEY` (in `~/.hermes/.env`). These had
   drifted (the key was later rotated for the Cloudflare tunnel), and re-syncing
   them fixed it.

With the gateway up and keys matched, Buddy greeted Aman aloud and held a real
conversation. The voice loop was complete.

### The setup script

Deployment used `scp` to copy the `buddy/` folder to the Pi, then a one-shot
`setup.sh` that installs system audio dependencies (`portaudio19-dev`,
`libasound2-dev`), the `uv` Python package manager, a Python 3.12 virtual
environment, and Pipecat with the needed extras:

```bash
uv pip install "pipecat-ai[deepgram,cartesia,silero,local]" \
  fastapi "uvicorn[standard]" openai python-dotenv
```

Keys live in `~/buddy/.env` (from a `.env.example` template), with
`HERMES_API_KEY` set to match the gateway's key.

---

## 8. Audio Engineering on the Pi

Getting audio working was, alongside the Wi-Fi country code, the other large time
sink — and the lesson is the same: **work at the operating-system level first,
and only move to Python once the OS can record and play sound.** Most "the bot is
broken" symptoms were really audio-routing problems underneath.

### The fundamental constraint

The Raspberry Pi 5 has **no analog headphone jack**. Sound can only leave the
board three ways: over HDMI (to a monitor's speakers), through a USB audio device,
or over Bluetooth. This shapes every decision below.

### Identifying devices

The two commands that list audio hardware:

```bash
arecord -l     # capture devices (microphones)
aplay -l       # playback devices (speakers)
```

In our setup `arecord -l` showed a single capture device, a USB dongle labeled
"KT USB Audio" (card 2). `aplay -l` showed *three* playback options: two HDMI
outputs (the Pi 5 has two HDMI ports, hence `vc4hdmi0` and `vc4hdmi1`) plus the
same USB device. The presence of multiple outputs is exactly why naive playback
tests can go to the wrong place and appear silent.

### First attempt: USB dongle + monitor speaker

The initial physical setup ran sound from the Pi over HDMI to the monitor, with
an external red speaker plugged into the *monitor's* headphone jack. The test we
ran addressed the USB device (`plughw:2,0`) — but that device was the *microphone*
path, not the route to the speaker. We were sending audio to a jack nothing was
listening on. A photo of the desk made the topology obvious: Pi → HDMI → monitor →
monitor's headphone-out → speaker, while we'd been testing the USB dongle.

The lesson: trace the *actual* physical audio path and test exactly that path,
device by device.

### Switching to Bluetooth earbuds

To simplify, Aman switched to a pair of Bluetooth earbuds (boAt Airdopes 141).
Pairing is done with `bluetoothctl`, an interactive tool:

```bash
bluetoothctl
  power on
  agent on
  scan on
  # wait for the device to appear with its MAC address, e.g. E1:29:03:26:78:DE
  pair E1:29:03:26:78:DE
  trust E1:29:03:26:78:DE
  connect E1:29:03:26:78:DE
  exit
```

> **Gotcha that cost real time:** Aman typed `pactl` and `arecord` commands *while
> still inside the `bluetoothctl` prompt*. The prompt showed `[Airdopes 141]>`,
> and `bluetoothctl` silently ignores commands it doesn't recognize — so the
> commands never ran and it looked like nothing was happening. You must `exit`
> bluetoothctl first. **If a terminal prompt shows an app name in brackets,
> you're inside that app's sub-shell, not the system shell.**

### The decisive audio bug: ALSA error 524

This was the heart of the audio trouble. Linux has two relevant audio layers:
**ALSA** (the low-level kernel sound system) and **PipeWire** (the modern
higher-level sound server that sits on top and does mixing, routing, and Bluetooth
audio). On current Raspberry Pi OS, PipeWire is the default — but the *bridge*
that lets old-style ALSA programs route through PipeWire is **not installed out of
the box.**

The symptom was that `pw-play` (which talks to PipeWire directly) produced sound
in the earbuds, but `aplay` and `speaker-test` (which talk to ALSA) failed:

```
ALSA lib pcm.c:2722:(snd_pcm_open_noupdate) Unknown PCM pulse
aplay: main:850: audio open error: No such file or directory
# and earlier:
Playback open error: -524,Unknown error 524
```

This matters enormously because **PyAudio — which Pipecat's LocalAudioTransport
uses — goes through ALSA.** So even though PipeWire worked, the voice bot's audio
path was broken.

The fix is one package that installs the ALSA→PipeWire bridge:

```bash
sudo apt install -y pipewire-alsa
systemctl --user restart pipewire wireplumber pipewire-pulse
aplay /usr/share/sounds/alsa/Front_Center.wav   # plain ALSA now works
```

After installing `pipewire-alsa`, the ALSA `default` device routes through
PipeWire, `aplay` works, and so does the Python bot.

> **Subtle trap:** `speaker-test` may *still* throw error 524 even after the fix,
> because of a quirk in how it opens the ALSA shim. Don't trust `speaker-test` as
> your source of truth — trust `aplay` and `pw-play`. We confirmed working audio
> with `aplay /usr/share/sounds/alsa/Front_Center.wav` and
> `pw-play /usr/share/sounds/alsa/Front_Center.wav`. (`pw-play` needs the
> `pipewire-bin` package; the older `paplay` needs `pulseaudio-utils`.)

### Volume and the default sink

Bluetooth volume is controlled through PipeWire's tooling, `wpctl`:

```bash
wpctl status                                  # shows sinks; "*" marks the default
wpctl set-volume @DEFAULT_AUDIO_SINK@ 1.0     # 100%
wpctl set-volume @DEFAULT_AUDIO_SINK@ 1.3     # boost past 100% (mild distortion risk)
```

`wpctl status` was also how we confirmed the earbuds were the default output sink
(it showed `* 78. Airdopes 141`) and that an input source existed for the mic.

### The Bluetooth mic problem: A2DP vs HFP

A subtle but important Bluetooth audio fact: a single Bluetooth device can operate
in different *profiles*, and they trade off quality against capability:

- **A2DP** — high-quality stereo audio, but **playback only** (no microphone).
  This is "music mode."
- **HFP (hands-free profile)** — enables the microphone, but drops audio to
  call-quality (mono, lower fidelity). This is "headset mode."

When you connect earbuds, they default to A2DP. So Buddy could *speak* through
them but couldn't *hear* — the mic wasn't available until we switched the profile:

```bash
pactl list cards short
pactl set-card-profile bluez_card.E1_29_03_26_78_DE headset-head-unit
```

Note the card name uses **underscores** instead of the colons in the MAC address.
After switching to `headset-head-unit`, the mic became available.

> **The honest tradeoff we flagged:** in HFP mode the audio is noticeably quieter
> and more muffled — that's inherent to the Bluetooth call profile, not a bug. A
> wired USB speakerphone would give both better loudness and clarity, and avoids
> the profile-switching entirely. Bluetooth also adds roughly 300–600 ms of
> round-trip latency on top of the pipeline. For a desk companion it's fine; for
> the best experience, wired wins.

### Picking devices in Python (when needed)

Because PipeWire presents a sensible default device, the bot usually needs no
explicit device selection. If the wrong device is ever picked, the helper script
lists what PyAudio sees:

```bash
python bot/list_audio_devices.py
```

and you set `input_device_index` / `output_device_index` in
`LocalAudioTransportParams` to the right index. We kept the defaults, since
PipeWire routed correctly to the earbuds.

---

## 9. The Wake Word: Full Implementation

This is the section the earlier summary glossed over, so here is the complete
design and implementation.

### The requirement and the engineering tradeoff

Aman wanted a wake word that was **dynamic** — settable to any phrase without
retraining a model — and asked for the lowest-latency option. Those two goals pull
against each other, so we laid out the real choices before picking:

| Engine | Latency | Custom phrase | Cost / catch |
|---|---|---|---|
| **Porcupine** (Picovoice) | Best (tens of ms) | Any phrase, generated instantly from a web console | Needs a free access key; custom keyword files expire ~monthly on the free tier |
| **openWakeWord** | Excellent | Any phrase, but **~20 min training** per word in a notebook | Fully open, no keys, no expiry |
| **Vosk + text match** | Good (slightly higher) | **Any phrase by editing a string** — no training, no keys | More CPU, marginally more false triggers |

Aman chose **Vosk + text match**, because "change it whenever I want by editing a
value" was the priority. This is the genuinely-dynamic option: the wake word is
just a string in a config file; there is no model to train and no key to manage.

### How we made Vosk fast and accurate: a constrained grammar

Vosk is a small offline speech-recognition engine. Used for open dictation it
would transcribe everything you say, which is both slower and prone to
mis-hearing the wake word. The trick we used is to **constrain Vosk's vocabulary
to just the wake phrase plus an "unknown" token.** This is done by passing a JSON
grammar to the recognizer:

```python
grammar = json.dumps(["hey buddy", "[unk]"])
recognizer = KaldiRecognizer(model, 16000, grammar)
```

With this grammar, Vosk only ever tries to decide "did they say *hey buddy*, or
something else (`[unk]`)?" That makes detection both **faster** (a tiny search
space) and **far more accurate** (it's not distracted by other words). And because
the grammar is rebuilt from the configured string, the wake word stays fully
dynamic — change the string, rebuild the recognizer, done.

### The architecture: a supervisor that hands off the microphone

There's a hard constraint to design around: **the wake listener and the voice bot
both need the microphone, and only one process can hold it at a time.** Our
solution is a supervisor pattern:

1. `wake_listener.py` holds the mic and runs Vosk continuously, listening only for
   the wake phrase.
2. When it hears the phrase, it **releases the microphone** (closes its audio
   stream) and **launches `bot.py` as a subprocess** for one conversation.
3. `bot.py` runs the full Pipecat pipeline, using the mic for the conversation.
4. When the conversation goes idle, `bot.py` **exits itself**, returning control.
5. The listener reopens the mic and resumes waiting for the wake word.

This cleanly avoids mic contention — at any moment exactly one of the two
processes owns the audio device.

### How the bot knows to exit: the idle watchdog

For the handoff to work, `bot.py` must end each conversation on its own after a
period of silence. This is implemented with two small pieces inside `bot.py`
(shown in full in Section 7), which are worth examining closely:

**The `IdleMonitor` frame processor.** Pipecat pipelines pass "frames" between
processors — frames for user speech, transcriptions, bot speech, audio, and so
on. We inserted a custom processor into the pipeline whose only job is to note the
time whenever a speech-related frame passes through it:

```python
class IdleMonitor(FrameProcessor):
    def __init__(self, state: dict):
        super().__init__()
        self._state = state

    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)
        if _ACTIVITY_FRAMES and isinstance(frame, _ACTIVITY_FRAMES):
            self._state["last"] = time.monotonic()
        await self.push_frame(frame, direction)
```

It updates `state["last"]` to "now" whenever it sees a frame that represents the
user or the bot talking, then passes the frame along unchanged. It's placed just
before the speaker in the pipeline so it observes both directions of speech.

**Defensive frame-type detection.** A nice robustness touch: rather than importing
specific frame classes (which could be renamed across Pipecat versions and crash
the bot on import), we probe for them by name and use whichever exist:

```python
_ACTIVITY_FRAMES = []
for _name in ("UserStartedSpeakingFrame", "UserStoppedSpeakingFrame",
              "TranscriptionFrame", "InterimTranscriptionFrame",
              "TTSStartedFrame", "TTSAudioRawFrame",
              "BotStartedSpeakingFrame", "BotStoppedSpeakingFrame"):
    try:
        _mod = __import__("pipecat.frames.frames", fromlist=[_name])
        _ACTIVITY_FRAMES.append(getattr(_mod, _name))
    except (ImportError, AttributeError):
        pass
_ACTIVITY_FRAMES = tuple(_ACTIVITY_FRAMES)
```

If a future Pipecat renames some of these, the bot still runs — it just uses the
ones that resolved.

**The watchdog coroutine.** A background async task checks once a second whether
the idle timeout has elapsed, and if so, ends the session:

```python
async def _idle_watchdog(state: dict):
    while True:
        await asyncio.sleep(1)
        if time.monotonic() - state["last"] > IDLE_TIMEOUT:
            logger.info(f"Idle for {IDLE_TIMEOUT:.0f}s — ending session.")
            os.kill(os.getpid(), signal.SIGINT)
            return
```

The elegant part is *how* it ends the session: `os.kill(os.getpid(),
signal.SIGINT)` sends the process the same signal as pressing **Ctrl+C**. We had
already observed in the logs that Ctrl+C triggers Pipecat's *clean* shutdown path
("interruption detected, cancelling"). So rather than inventing a new shutdown
mechanism that might leave audio devices or websockets in a bad state, we reuse
the one we know works gracefully. The process exits, and the supervisor resumes.

### The complete `wake_listener.py`, explained

```python
"""Always-on wake-word listener for Buddy.

Listens continuously with a small offline Vosk model. When it hears the wake
phrase, it launches the Pipecat voice bot (bot.py) for one conversation, then
returns to listening when that session ends.

The wake phrase comes from buddy_config.json (editable in the web UI) and is
live-reloaded — change it and the listener picks it up within seconds, no
restart. Vosk's vocabulary is constrained to the phrase for fast, low-false
detection.
"""

import json
import os
import subprocess
import sys
import time

import pyaudio
from dotenv import load_dotenv
from vosk import KaldiRecognizer, Model, SetLogLevel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_store import config_mtime, load_config  # noqa: E402

load_dotenv(override=True)
SetLogLevel(-1)  # silence Vosk's verbose kaldi logging

MODEL_PATH = os.path.expanduser(
    os.getenv("VOSK_MODEL_PATH", "~/buddy/models/vosk-small-en")
)

HERE = os.path.dirname(os.path.abspath(__file__))
BUDDY_DIR = os.path.dirname(HERE)
BOT = os.path.join(HERE, "bot.py")

RATE = 16000
CHUNK = 4000  # 0.25s blocks


def make_recognizer(model: Model, wake_word: str) -> KaldiRecognizer:
    """Constrain recognition to the wake phrase plus 'unknown' for speed/accuracy."""
    grammar = json.dumps([wake_word, "[unk]"])
    return KaldiRecognizer(model, RATE, grammar)


def listen_for_wake(model: Model) -> None:
    """Block until the wake phrase is heard. Live-reloads the phrase if changed."""
    wake_word = load_config()["wake_word"]
    seen_mtime = config_mtime()

    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.paInt16, channels=1, rate=RATE,
        input=True, frames_per_buffer=CHUNK,
    )
    rec = make_recognizer(model, wake_word)
    print(f"[wake] listening for: '{wake_word}'  (Ctrl+C to quit)")
    try:
        while True:
            # Live-reload: if the config file changed, rebuild for the new word.
            if config_mtime() != seen_mtime:
                wake_word = load_config()["wake_word"]
                seen_mtime = config_mtime()
                rec = make_recognizer(model, wake_word)
                print(f"[wake] wake word updated → '{wake_word}'")

            data = stream.read(CHUNK, exception_on_overflow=False)
            if rec.AcceptWaveform(data):
                text = json.loads(rec.Result()).get("text", "")
            else:
                text = json.loads(rec.PartialResult()).get("partial", "")
            if wake_word in text.lower():
                return
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()


def main() -> None:
    if not os.path.isdir(MODEL_PATH):
        sys.exit(
            f"[wake] Vosk model not found at {MODEL_PATH}\n"
            f"       Run: bash setup_wakeword.sh"
        )
    model = Model(MODEL_PATH)
    print(f"[wake] model loaded from {MODEL_PATH}")

    while True:
        listen_for_wake(model)
        print("[wake] detected — starting Buddy")
        subprocess.run([sys.executable, BOT], cwd=BUDDY_DIR)
        print("[wake] session ended — back to listening")
        time.sleep(1)  # let the audio device settle before reopening


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[wake] stopped")
```

**Loading the model.** `Model(MODEL_PATH)` loads the small English Vosk model
(downloaded by `setup_wakeword.sh`, ~40MB) once at startup. `SetLogLevel(-1)`
silences Vosk's noisy internal logging.

**The audio parameters.** `RATE = 16000` (16 kHz) is the sample rate Vosk expects;
`CHUNK = 4000` reads audio in quarter-second blocks. The stream is mono 16-bit
PCM, opened with PyAudio.

**The detection loop.** Inside `listen_for_wake`, we read audio block by block and
feed each block to the recognizer. Vosk distinguishes *final* results
(`AcceptWaveform` returns true — a complete utterance) from *partial* results
(speech in progress). We check both, lowercase the text, and trigger the moment
the wake word appears as a substring. Checking partials means we can fire as soon
as the phrase is recognized, shaving latency rather than waiting for the utterance
to finish.

**Live reload of the wake word.** This is the feature that makes the wake word
truly dynamic without a restart. At the top of each loop iteration, we check the
config file's modification time (`config_mtime()`). If it changed — because the
user saved a new wake word in the web UI — we reload the config and rebuild the
recognizer with the new grammar on the fly, printing
`[wake] wake word updated → '...'`. Since the loop runs every quarter-second, a
change takes effect almost immediately.

**The supervisor loop.** `main()` is an infinite loop: wait for the wake word,
then `subprocess.run([sys.executable, BOT], cwd=BUDDY_DIR)` launches `bot.py`
using the same Python interpreter (so it runs inside the virtualenv) with the
working directory set to `~/buddy` (so `bot.py`'s `load_dotenv` finds the `.env`
there). `subprocess.run` blocks until `bot.py` exits — which it does after the
idle timeout — and then we sleep one second to let the audio device settle before
reopening it for the next listen. Critically, the `try/finally` in
`listen_for_wake` ensures the mic stream is always closed before we hand off to
the bot, so there's no contention.

### The wake-word setup script

`setup_wakeword.sh` installs Vosk into the venv and downloads the model:

```bash
source .venv/bin/activate
~/.local/bin/uv pip install vosk
mkdir -p models && cd models
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
mv vosk-model-small-en-us-0.15 vosk-small-en
```

### The result

In testing, the wake word worked on the first real try. Aman says "hey buddy" (or
whatever phrase is configured), the listener detects it, launches the bot, Buddy
greets him in the earbuds, they converse, and after the idle timeout the bot exits
and the listener quietly resumes. Changing the wake word later is a one-field edit
in the web UI that takes effect within seconds.

---

## 10. The Shared Config Store

Before building the web UI, we needed a clean answer to a coordination problem:
**three separate processes** (the wake listener, the bot, and the web server) all
need to read and write the same user settings. The solution is a single JSON file
as the source of truth, accessed through one shared module so the logic lives in
exactly one place.

### The complete `config_store.py`, explained

```python
"""Shared config for Buddy — the single source of truth.

The wake listener, the voice bot, and the config web server all read and write
this one JSON file (~/buddy/buddy_config.json). Keeping it in one place means
the UI can change the wake word or system prompt and the other processes pick
the change up without code edits.

Secrets (API keys) stay in .env — this file is only user-tunable behavior.
"""

import json
import os
import threading

CONFIG_PATH = os.path.expanduser(
    os.getenv("BUDDY_CONFIG_PATH", "~/buddy/buddy_config.json")
)

DEFAULTS = {
    "wake_word": "hey buddy",
    "system_prompt": (
        "You are Buddy, a warm and friendly voice companion on Aman's desk. "
        "Keep replies short and conversational since they are spoken aloud. "
        "Avoid markdown, lists, or any symbols that don't read well as speech."
    ),
    "idle_timeout": 30,
}

_lock = threading.Lock()


def load_config() -> dict:
    """Return the saved config merged over defaults (missing keys filled in)."""
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH) as f:
            saved = json.load(f)
        if isinstance(saved, dict):
            cfg.update({k: saved[k] for k in DEFAULTS if k in saved})
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return cfg


def save_config(updates: dict) -> dict:
    """Merge `updates` into the saved config (validated) and write atomically."""
    with _lock:
        cfg = load_config()
        if "wake_word" in updates:
            wake = str(updates["wake_word"]).strip().lower()
            if wake:
                cfg["wake_word"] = wake
        if "system_prompt" in updates:
            cfg["system_prompt"] = str(updates["system_prompt"]).strip()
        if "idle_timeout" in updates:
            try:
                cfg["idle_timeout"] = max(5, min(600, int(updates["idle_timeout"])))
            except (TypeError, ValueError):
                pass

        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        tmp = CONFIG_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(cfg, f, indent=2)
        os.replace(tmp, CONFIG_PATH)  # atomic — readers never see a half-write
    return cfg


def config_mtime() -> float:
    """Last-modified time of the config file, or 0 if it doesn't exist yet."""
    try:
        return os.path.getmtime(CONFIG_PATH)
    except OSError:
        return 0.0
```

**Defaults merged under saved values.** `load_config` always starts from
`DEFAULTS` and overlays whatever is saved, so a missing or partial config file
never produces missing keys — every reader gets a complete dict. A corrupt file
(JSON decode error) falls back to defaults rather than crashing.

**Validation on save.** `save_config` doesn't blindly trust input: the wake word
is stripped and lowercased (and ignored if empty), the system prompt is stripped,
and the idle timeout is clamped to a sane 5–600 second range. This matters because
the values come from a web form.

**Atomic writes.** The write goes to a temporary file first, then
`os.replace(tmp, CONFIG_PATH)` swaps it in atomically. This guarantees that a
reader (like the wake listener polling the file every quarter-second) never reads
a half-written file. A `threading.Lock` serializes concurrent saves.

**The mtime helper.** `config_mtime` exposes the file's last-modified time, which
is exactly what the wake listener polls to detect changes and trigger its live
reload (Section 9). This is a deliberately lightweight change-detection mechanism
— no file watching, no message bus, just comparing a timestamp.

**The boundary between config and secrets.** A clear design rule: user-tunable
*behavior* (wake word, prompt, timeout) lives in this JSON, while *secrets* (API
keys) stay in `.env`. The web UI only ever touches the JSON, so it can't leak or
mangle keys.

---

## 11. The FastAPI Configuration Server

With the shared store in place, we built a small **FastAPI** web service so Aman
could change settings from a browser instead of editing files over SSH. FastAPI
was a natural fit: it's already a dependency (installed during voice-bot setup via
`uvicorn`), and it makes a typed JSON API plus static file serving trivial.

### The complete `server.py`, explained

```python
"""Buddy config server — a small FastAPI app to tune Buddy from a browser."""

import os
import sys

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_store import DEFAULTS, load_config, save_config  # noqa: E402
import wifi_manager  # noqa: E402
import bt_manager  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = os.getenv("BUDDY_CONFIG_HOST", "0.0.0.0")
PORT = int(os.getenv("BUDDY_CONFIG_PORT", "8080"))

app = FastAPI(title="Buddy Config", version="1.0.0")


class ConfigUpdate(BaseModel):
    wake_word: str | None = None
    system_prompt: str | None = None
    idle_timeout: int | None = None


class WifiConnect(BaseModel):
    ssid: str
    password: str | None = None


class WifiRadio(BaseModel):
    enabled: bool


class BtMac(BaseModel):
    mac: str


class BtPower(BaseModel):
    enabled: bool


@app.get("/api/config")
def get_config():
    return load_config()


@app.put("/api/config")
def put_config(update: ConfigUpdate):
    saved = save_config(update.model_dump(exclude_none=True))
    return {
        "ok": True,
        "config": saved,
        "note": (
            "Wake word applies within a few seconds (listener live-reloads). "
            "System prompt and idle timeout apply on the next conversation."
        ),
    }


@app.get("/api/defaults")
def get_defaults():
    return DEFAULTS


# --- Wi-Fi management -------------------------------------------------------

@app.get("/api/wifi/status")
def wifi_status():
    return wifi_manager.status()


@app.get("/api/wifi/scan")
def wifi_scan():
    return wifi_manager.scan()


@app.post("/api/wifi/connect")
def wifi_connect(req: WifiConnect):
    ok, message = wifi_manager.connect(req.ssid, req.password)
    return {"ok": ok, "message": message}


@app.post("/api/wifi/radio")
def wifi_radio(req: WifiRadio):
    ok, message = wifi_manager.set_radio(req.enabled)
    return {"ok": ok, "message": message}


# --- Bluetooth management ---------------------------------------------------

@app.get("/api/bt/devices")
def bt_devices():
    return bt_manager.list_devices()


@app.get("/api/bt/scan")
def bt_scan():
    return bt_manager.scan()


@app.post("/api/bt/power")
def bt_power(req: BtPower):
    ok, message = bt_manager.set_power(req.enabled)
    return {"ok": ok, "message": message}


@app.post("/api/bt/connect")
def bt_connect(req: BtMac):
    ok, message = bt_manager.connect(req.mac)
    return {"ok": ok, "message": message}


@app.post("/api/bt/disconnect")
def bt_disconnect(req: BtMac):
    ok, message = bt_manager.disconnect(req.mac)
    return {"ok": ok, "message": message}


@app.get("/")
def index():
    return FileResponse(os.path.join(HERE, "index.html"))


app.mount("/static", StaticFiles(directory=HERE), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
```

**Pydantic request models.** Each `BaseModel` subclass (`ConfigUpdate`,
`WifiConnect`, etc.) declares the JSON shape an endpoint accepts. FastAPI uses
these to validate incoming requests automatically and to reject malformed input
before our code runs — the typing *is* the validation.

**The config endpoints.** `GET /api/config` returns current settings; `PUT
/api/config` saves them (using `model_dump(exclude_none=True)` so only the fields
the client actually sent are applied) and returns a human-readable note about when
each change takes effect.

**Delegation to managers.** The Wi-Fi and Bluetooth endpoints are thin — they call
into `wifi_manager` and `bt_manager` (Sections 12 and 13) and return
`{ok, message}`. Keeping the system-command logic in separate modules keeps the
web layer clean and testable.

**Serving the UI.** `GET /` returns the single-page `index.html`. The whole front
end is one self-contained HTML file.

**Binding.** It listens on `0.0.0.0:8080` by default, reachable from any device on
the LAN (so Aman opens it from his Mac at `http://192.168.1.10:8080`).

### The front end

The UI is a single `index.html` (~350 lines) — plain HTML, CSS, and vanilla
JavaScript, no framework. It has three sections (config, Wi-Fi, Bluetooth) and
talks to the API with `fetch`. It uses the browser's `color-scheme: light dark`
and CSS `color-mix` so it looks right in both light and dark mode, and it's
mobile-friendly. The full source is in Appendix C; the Wi-Fi and Bluetooth
behaviors are discussed in their sections below. When first loaded it showed the
three fields populated from the Pi, and saving showed a green confirmation.

---

## 12. Wi-Fi Management from the Browser

The next request was to manage the Pi's Wi-Fi from the UI: see status, scan for
networks, connect to a different router, and turn the radio on/off. This is done
by shelling out to `nmcli` (NetworkManager's CLI).

### The complete `wifi_manager.py`, explained

```python
"""Wi-Fi control for the Buddy config server, via NetworkManager (nmcli)."""

import re
import subprocess


def _run(args, timeout=60):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except subprocess.TimeoutExpired:
        return 124, "", "timed out"
    except FileNotFoundError:
        return 127, "", "nmcli not found"


def _split_terse(line):
    """Split an `nmcli -t` line on unescaped colons and unescape the fields."""
    fields = re.split(r"(?<!\\):", line)
    return [f.replace("\\:", ":").replace("\\\\", "\\") for f in fields]


def status():
    """Return {enabled, active_ssid, ip}."""
    _, radio, _ = _run(["nmcli", "-t", "-f", "WIFI", "radio"], timeout=10)
    enabled = radio.strip().endswith("enabled")

    active_ssid = None
    _, out, _ = _run(["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"], timeout=10)
    for line in out.splitlines():
        parts = _split_terse(line)
        if parts and parts[0] == "yes":
            active_ssid = parts[1] if len(parts) > 1 else None
            break

    _, ipout, _ = _run(["hostname", "-I"], timeout=10)
    ip = ipout.split()[0] if ipout else None
    return {"enabled": enabled, "active_ssid": active_ssid, "ip": ip}


def scan():
    """Return a list of nearby networks, strongest signal first, de-duplicated."""
    # `--rescan yes` forces a fresh scan and WAITS for results, rather than
    # returning the stale cache (which is just the connected network).
    _, out, err = _run(
        ["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY",
         "dev", "wifi", "list", "--rescan", "yes"],
        timeout=30,
    )
    if err and not out:
        return {"ok": False, "error": err, "networks": []}

    best = {}
    for line in out.splitlines():
        parts = _split_terse(line)
        if len(parts) < 4:
            continue
        in_use, ssid, signal, security = parts[0], parts[1], parts[2], parts[3]
        if not ssid:
            continue  # hidden network
        try:
            sig = int(signal)
        except ValueError:
            sig = 0
        if ssid not in best or sig > best[ssid]["signal"]:
            best[ssid] = {
                "ssid": ssid,
                "signal": sig,
                "security": security or "open",
                "in_use": in_use == "*",
            }
    nets = sorted(best.values(), key=lambda n: n["signal"], reverse=True)
    return {"ok": True, "networks": nets}


def connect(ssid: str, password: str | None):
    """Connect to an SSID. Returns (ok, message)."""
    if not ssid:
        return False, "SSID is required"
    args = ["nmcli", "dev", "wifi", "connect", ssid]
    if password:
        args += ["password", password]
    rc, out, err = _run(args, timeout=75)
    return rc == 0, (out or err or "done")


def set_radio(enabled: bool):
    """Turn the Wi-Fi radio on or off. Returns (ok, message)."""
    rc, out, err = _run(["nmcli", "radio", "wifi", "on" if enabled else "off"], timeout=20)
    return rc == 0, (out or err or "done")
```

**The `_run` wrapper.** Every system command goes through this, which captures
stdout/stderr, enforces a timeout, and returns a consistent
`(returncode, stdout, stderr)` tuple — handling "command not found" and "timed
out" gracefully rather than throwing.

**Parsing `nmcli -t` output.** The `-t` flag makes nmcli emit terse,
colon-separated output — except values can themselves contain colons (a Wi-Fi name
like `My:Net`), which nmcli escapes as `\:`. The `_split_terse` helper splits only
on *unescaped* colons (a regex with a negative lookbehind, `(?<!\\):`) and
unescapes the fields. We verified it against `yes:My\:Net:72:WPA2`, which
correctly parses to `['yes', 'My:Net', '72', 'WPA2']`.

**Status, scan, connect, radio.** `status` reports radio state, connected SSID,
and IP. `scan` lists nearby networks de-duplicated by SSID (keeping the strongest
signal) and sorted strongest-first. `connect` joins a network. `set_radio` toggles
the radio.

### The bug: scan only ever showed the connected network

When Aman first hit "Scan," only his own router appeared — not even neighbors, and
not his phone hotspot. We debugged methodically:

**Step 1 — my code or the radio?** We ran the raw command the server uses:
`nmcli dev wifi list --rescan yes`. It *also* showed only one network — so it
wasn't a parsing bug; NetworkManager itself saw only one.

**Step 2 — can the radio see more?** A low-level scan bypassing NetworkManager:

```bash
sudo iw dev wlan0 scan | grep SSID
```

returned **eight** networks. So the radio was fully capable — NetworkManager was
the restricted layer.

**Step 3 — the root cause, again.** `iw reg get | grep country` showed
`country 99: DFS-UNSET` — **unset**, the same regulatory-domain family of problem
from the first Wi-Fi saga. An unset regdomain makes NetworkManager conservative
about which channels it surfaces. The country code hadn't fully applied because
the Broadcom chip needs a reboot to pick it up:

```bash
sudo raspi-config nonint do_wifi_country IN
sudo reboot
# after reconnecting:
iw reg get | grep country            # now "country IN:"
nmcli dev wifi list --rescan yes      # now shows all eight networks
```

After the reboot the web UI listed everything. (A lingering `country 99` on the
Broadcom chip's own line is a harmless "self-managed regdomain" quirk once the
global domain is set.)

**A secondary code fix.** The first `scan()` called a separate
`nmcli dev wifi rescan` then immediately listed — but scanning is *asynchronous*,
so it returned the stale cache before fresh results arrived. We switched to
`nmcli dev wifi list --rescan yes`, which forces a scan and **waits** for results
in one call.

### The safety guardrails in the UI

Managing Wi-Fi *over* Wi-Fi is a genuine footgun: switching networks or disabling
the radio can disconnect the Pi from the very network serving the page. So the
front end adds confirmations. Connecting to a different network warns the page may
freeze and the Pi will move to a new IP. Stopping Wi-Fi warns, strongly, that
you'll lose access entirely and can only recover with Ethernet or a
monitor+keyboard. The JavaScript even anticipates the request never returning
(because the Pi switched networks mid-request) and shows a helpful message rather
than a confusing error.

### Permissions

These `nmcli` commands run as the normal `aman` user, not root, because Raspberry
Pi OS puts the default user in the `netdev` group with a polkit rule allowing
NetworkManager control without `sudo`. We confirmed both `nmcli` (as user) and
`sudo nmcli` returned the same full list after the regdomain fix.

---

## 13. Bluetooth Management from the Browser

The final UI feature mirrors Wi-Fi for Bluetooth: power the adapter on/off, scan,
and connect/disconnect devices — built on `bluetoothctl`, the same tool Aman had
already used by hand to pair the earbuds (so the permissions were known good).

### The complete `bt_manager.py`, explained

```python
"""Bluetooth control for the Buddy config server, via bluetoothctl (BlueZ)."""

import re
import subprocess

_DEVICE_RE = re.compile(r"Device ([0-9A-Fa-f:]{17})\s+(.*)")


def _bt(args, timeout=15):
    """Run `bluetoothctl <args>` and return (rc, stdout, stderr)."""
    try:
        p = subprocess.run(
            ["bluetoothctl", *args], capture_output=True, text=True, timeout=timeout
        )
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except subprocess.TimeoutExpired:
        return 124, "", "timed out"
    except FileNotFoundError:
        return 127, "", "bluetoothctl not found"


def _parse_devices(text):
    out = {}
    for line in text.splitlines():
        m = _DEVICE_RE.search(line)
        if m:
            mac, name = m.group(1).upper(), m.group(2).strip()
            out[mac] = name or mac
    return out


def _macs(subfilter):
    """MAC set from `bluetoothctl devices <subfilter>` (e.g. Connected, Paired)."""
    _, out, _ = _bt(["devices", subfilter], timeout=10)
    return set(_parse_devices(out).keys())


def powered():
    _, out, _ = _bt(["show"], timeout=10)
    return "Powered: yes" in out


def set_power(on: bool):
    rc, out, err = _bt(["power", "on" if on else "off"], timeout=10)
    ok = "succeeded" in out.lower() or rc == 0
    return ok, (out or err or "done")


def list_devices():
    """Known devices with connected/paired flags."""
    _, out, _ = _bt(["devices"], timeout=10)
    known = _parse_devices(out)
    connected = _macs("Connected")
    paired = _macs("Paired") or set()
    devices = [
        {
            "mac": mac,
            "name": name,
            "connected": mac in connected,
            "paired": mac in paired,
        }
        for mac, name in known.items()
    ]
    devices.sort(key=lambda d: (not d["connected"], not d["paired"], d["name"].lower()))
    return {"powered": powered(), "devices": devices}


def scan(seconds: int = 8):
    """Timed discovery scan, then return the (now larger) device list."""
    if not powered():
        _bt(["power", "on"], timeout=10)
    # Blocks for `seconds`, discovering nearby devices.
    _bt(["--timeout", str(seconds), "scan", "on"], timeout=seconds + 10)
    return list_devices()


def connect(mac: str):
    if not mac:
        return False, "MAC address required"
    # Pair + trust are no-ops if already done; connect is what matters.
    _bt(["pair", mac], timeout=25)
    _bt(["trust", mac], timeout=10)
    rc, out, err = _bt(["connect", mac], timeout=25)
    ok = "Connection successful" in out or (rc == 0 and "Failed" not in out)
    return ok, (out or err or "done")


def disconnect(mac: str):
    if not mac:
        return False, "MAC address required"
    rc, out, err = _bt(["disconnect", mac], timeout=15)
    ok = "Successful disconnected" in out or "successful" in out.lower() or rc == 0
    return ok, (out or err or "done")
```

**Non-interactive bluetoothctl.** Modern `bluetoothctl` accepts subcommands as
arguments (`bluetoothctl power on`, `bluetoothctl devices`, `bluetoothctl connect
MAC`), so we script it rather than driving the interactive prompt. The `_bt`
helper wraps each call with the same timeout/error handling as the Wi-Fi module.

**Parsing device lists.** `bluetoothctl devices` outputs lines like
`Device E1:29:03:26:78:DE Airdopes 141`. The regex `_DEVICE_RE` extracts the
17-character MAC and the name. We verified it handles plain and tab-indented
lines.

**Connected/paired flags.** BlueZ supports filtered listings — `bluetoothctl
devices Connected` and `devices Paired` — so `list_devices` cross-references the
full list against those sets to mark each device's state, then sorts connected
first, then paired, then alphabetically.

**Timed scan.** `bluetoothctl --timeout 8 scan on` runs an 8-second discovery and
returns automatically — ideal for a "Scan" button.

**Robust connect.** `connect` runs pair → trust → connect. Pair and trust are
harmless no-ops if the device is already bonded (as the Airdopes were), but
including them means a brand-new device works in a single click.

### The important caveat

Connecting an audio device through this UI gives **playback**, but using its
**microphone** requires switching to the HFP `headset-head-unit` profile, which
BlueZ pairing alone doesn't do (see the audio section). So if a user connects
earphones here and Buddy can speak but not hear, that's the A2DP-vs-HFP profile
issue, not a connect bug. A "use as Buddy's mic+speaker" action that also flips
the PipeWire card profile could be added if desired.

---

## 14. Telegram Integration

We connected the same Hermes brain to Telegram, so Buddy can be messaged from a
phone anywhere — sharing the same memory, skills, and tools as the voice
interface. Telegram support is built into the `hermes gateway`, so this was
configuration, not new code.

### The steps

1. **Get a bot token** from `@BotFather` on Telegram (`/newbot`, or `/token` for
   an existing bot). It looks like `123456789:ABCdefGHI...`.
2. **Get your numeric user ID** from `@userinfobot` — it replies with your ID.
   This goes on the allowlist so only you can command the agent.
3. **Add both to `~/.hermes/.env`:**

```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHI...
TELEGRAM_ALLOWED_USERS=6168832341
```

4. **Restart the gateway** (`Ctrl+C`, then `hermes gateway`).

### The gotcha

On the first attempt the gateway logged `Unauthorized user: 6168832341 (Aman
Khandelwal) on telegram` — it *saw* the message and identified Aman, but rejected
him. The cause was an `@` accidentally prefixing the ID in the env file
(`TELEGRAM_ALLOWED_USERS=@6168832341`). The allowlist expects a **bare numeric
ID**. Removing the `@` fixed it:

```bash
sed -i 's/^TELEGRAM_ALLOWED_USERS=@/TELEGRAM_ALLOWED_USERS=/' ~/.hermes/.env
```

### Why the allowlist matters so much here

This is not a cosmetic setting. The Hermes agent has terminal access to the Pi. If
the bot were open to anyone (the tempting `GATEWAY_ALLOW_ALL_USERS=true`, which the
startup also warns about), any Telegram user who found the bot could run commands
on the device. Keeping `TELEGRAM_ALLOWED_USERS` set to **only the owner's ID** is
the lock on that door.

---

## 15. Remote Access, Autonomy, and Security

### Maximum autonomy

Aman wanted Buddy to act without asking permission — open the browser, open a
terminal, run any command. Hermes has a setting for this:

```bash
hermes config set approvals.mode off          # skip all approval prompts (YOLO)
hermes config set security.tirith_enabled false  # disable the command safety scanner
```

`approvals.mode off` is documented as equivalent to `HERMES_YOLO_MODE=true` and
disables all approval checks for terminal commands. `tirith_enabled false` turns
off the scanner that pre-screens commands for danger. These make the agent fully
autonomous — appropriate only on a trusted, ideally non-internet-exposed device.

### Exposing the API with a Cloudflare tunnel

To reach the Hermes API from outside the home network, we used a **Cloudflare
quick tunnel** — the Pi makes an *outbound* connection to Cloudflare, so there's
no router port-forwarding and the home IP stays hidden:

```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb -o /tmp/cloudflared.deb
sudo dpkg -i /tmp/cloudflared.deb
cloudflared tunnel --url http://localhost:8642
```

It prints a public `https://<random>.trycloudflare.com` URL. The quick tunnel is
temporary — the URL changes each restart. A named tunnel (with a Cloudflare
account and your own domain) gives a stable URL and runs as a service, which is
the next step if a permanent address is wanted.

### The security reality, stated plainly

Combining **autonomy off** with a **public tunnel** is powerful and dangerous:
anyone holding the tunnel URL + API key has near-root control of the Pi. So, as
part of enabling the tunnel, we **rotated the weak `change-me-local-dev` key to a
strong random one**:

```bash
NEW_KEY=$(openssl rand -hex 24)
sed -i "s/^API_SERVER_KEY=.*/API_SERVER_KEY=$NEW_KEY/" ~/.hermes/.env
sed -i "s/^HERMES_API_KEY=.*/HERMES_API_KEY=$NEW_KEY/" ~/buddy/.env
```

(Note this is also why the voice bot later hit a key mismatch — the rotation
updated both files, but it's a reminder that the bot's key must always equal the
gateway's.) The guidance we gave: treat the key like a password, and **kill the
`cloudflared` process whenever remote access isn't actively needed.** On a local
network alone the setup is reasonable; fully open *and* fully public is asking for
trouble.

### Viewing the Hermes dashboard

As covered in Section 6, the dashboard runs locally on `:9119` and is best reached
from the Mac via an SSH tunnel (`ssh -L 9119:localhost:9119 aman@192.168.1.10`),
keeping it off the network while still viewable.

---

## 16. Packaging Everything as a Reusable Skill

To make the whole build repeatable, we packaged it as an installable **skill** —
a bundle containing a `SKILL.md` (the workflow and triggering description), two
reference documents (`hardware-and-flashing.md` and `troubleshooting.md`), and a
`scripts/` folder with all the working code. The idea: a future build (by Aman or
anyone) starts from running code and a troubleshooting guide rather than a blank
page, and an assistant with the skill installed can recognize "set up a Pi voice
assistant" requests and follow the proven path.

The skill was zipped as `buddy-pi-companion.skill` and presented for installation
(it lands in the assistant's Settings → Capabilities). Its description is tuned to
trigger on requests about Pi voice assistants, headless flashing, Pipecat, Hermes
agents, wake words, Pi audio troubleshooting, and exposing a local LLM over an
OpenAI-compatible API — even when the user doesn't name those tools explicitly.

---

## Appendix A: The Gotchas, Collected

The issues that cost the most time, gathered so they can be skipped next time.

1. **Wi-Fi country code (first boot).** Wrong/unset country code in Raspberry Pi
   Imager → the radio is software-blocked (`sw disabled`) and the Pi shows
   `127.0.0.1` only. Fix: `sudo raspi-config nonint do_wifi_country IN`,
   `sudo rfkill unblock wifi`, `nmcli radio wifi on`. Set it correctly at flash
   time to avoid entirely.

2. **Wi-Fi country code (scanning).** The *same* unset regdomain (`iw reg get` →
   `country 99`) makes `nmcli` scans show only the connected network even though
   the radio sees many (`sudo iw dev wlan0 scan`). Fix: set the country and
   **reboot** (the Broadcom chip needs it), and use `nmcli dev wifi list --rescan
   yes` (forces a scan and waits, vs. returning stale cache).

3. **ALSA error 524 / "Unknown PCM".** PipeWire is the default sound server but
   the ALSA bridge isn't installed, so `aplay` and PyAudio (and therefore the
   voice bot) can't play sound while `pw-play` can. Fix:
   `sudo apt install -y pipewire-alsa` and restart the PipeWire user services.
   Note `speaker-test` may still throw 524 even when fixed — trust `aplay`/`pw-play`.

4. **Bluetooth mic silent.** A connected audio device defaults to A2DP (playback
   only). The mic needs the HFP profile:
   `pactl set-card-profile bluez_card.XX_XX_... headset-head-unit` (MAC uses
   underscores). Tradeoff: HFP is call-quality audio.

5. **Commands "do nothing."** Typing `pactl`/`arecord`/`nmcli` while still inside
   the interactive `bluetoothctl` prompt — it silently ignores them. `exit` first.
   The prompt showing an app name in brackets (`[Airdopes 141]>`) is the tell.

6. **Hermes "Connection error" from the bot.** The gateway isn't running, or the
   bot's `HERMES_API_KEY` ≠ the gateway's `API_SERVER_KEY` (easy to desync after a
   key rotation). Check `curl http://127.0.0.1:8642/health` and compare the keys.

7. **OpenAI speech services for voice.** Erroring and 8–10s time-to-first-byte;
   also a ChatGPT/Codex subscription doesn't cover the audio *API*. Use streaming
   specialists (Deepgram + Cartesia) instead.

8. **Telegram "Unauthorized user."** `TELEGRAM_ALLOWED_USERS` must be a bare
   numeric ID — an `@` prefix causes rejection even though the gateway recognizes
   the user.

9. **`.local` hostnames are flaky.** Use the Pi's IP address (from the router)
   rather than `buddy.local` for SSH and the web UI.

10. **`scp` runs on the Mac, not the Pi.** Copying files *to* the Pi must be run
    from the Mac's shell; running it inside an SSH session looks for the source on
    the Pi and fails.

---

## Appendix B: Complete Command Reference

### Brain (Hermes)

```bash
# install
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
source ~/.bashrc
hermes model                      # choose provider + key
# enable API server (in ~/.hermes/.env): API_SERVER_ENABLED=true, API_SERVER_KEY=...
hermes gateway                    # run the brain + API server (:8642) + Telegram
hermes dashboard                  # local web dashboard (:9119)
hermes doctor                     # diagnostics
hermes config set approvals.mode off            # full autonomy
hermes config set security.tirith_enabled false
```

### Verifying the API

```bash
curl http://localhost:8642/health
curl http://localhost:8642/v1/chat/completions \
  -H "Authorization: Bearer <API_SERVER_KEY>" -H "Content-Type: application/json" \
  -d '{"model":"hermes-agent","messages":[{"role":"user","content":"Hello!"}]}'
```

### Voice + wake word (on the Pi, in ~/buddy)

```bash
bash setup.sh                                   # audio deps, venv, Pipecat
bash setup_wakeword.sh                           # Vosk + model
source .venv/bin/activate
python bot/bot.py                                # one always-on session
python bot/wake_listener.py                      # wake-word supervisor
python bot/list_audio_devices.py                 # list audio devices
python config_server/server.py                   # config web UI (:8080)
```

### Audio

```bash
arecord -l ; aplay -l                            # list mics / speakers
sudo apt install -y pipewire-alsa                # fix ALSA 524
aplay /usr/share/sounds/alsa/Front_Center.wav    # test playback
arecord -f S16_LE -r 16000 -V mono -d 5 t.wav && aplay t.wav   # test mic
wpctl status                                     # default sink, volume
wpctl set-volume @DEFAULT_AUDIO_SINK@ 1.0
pactl set-card-profile bluez_card.XX_XX_XX_XX_XX_XX headset-head-unit   # BT mic
```

### Bluetooth (manual)

```bash
bluetoothctl
  power on ; agent on ; scan on
  pair MAC ; trust MAC ; connect MAC
  exit
```

### Wi-Fi / network

```bash
nmcli dev wifi list --rescan yes                 # scan (waits for results)
sudo nmcli dev wifi connect "SSID" password "PW"
sudo raspi-config nonint do_wifi_country IN ; sudo reboot
iw reg get | grep country                        # check regdomain
sudo iw dev wlan0 scan | grep SSID               # low-level scan
```

### Deploying from the Mac

```bash
scp -r "/path/to/buddy" aman@192.168.1.10:~/     # whole folder
scp "/path/to/buddy/bot/bot.py" aman@192.168.1.10:~/buddy/bot/   # one file
```

---

## Appendix C: Full File Tree and Deployment

### File tree (on the Pi, under `~/buddy/`)

```
~/buddy/
├── .env                      # secrets: DEEPGRAM_API_KEY, CARTESIA_API_KEY, HERMES_API_KEY
├── .env.example              # template for the above
├── buddy_config.json         # shared settings (created on first save)
├── config_store.py           # shared config module
├── wifi_manager.py           # nmcli wrapper
├── bt_manager.py             # bluetoothctl wrapper
├── setup.sh                  # installs audio deps + venv + Pipecat
├── setup_wakeword.sh         # installs Vosk + model
├── models/
│   └── vosk-small-en/        # Vosk model (~40MB, downloaded)
├── bot/
│   ├── bot.py                # the Pipecat voice pipeline
│   ├── wake_listener.py      # the wake-word supervisor
│   └── list_audio_devices.py # audio device helper
└── config_server/
    ├── server.py             # FastAPI config server
    └── index.html            # the single-page web UI
```

Plus, outside `~/buddy/`, the Hermes agent at `~/.hermes/` (config.yaml, .env,
hermes-agent/) installed by its own installer.

### The three processes to run

For a fully operational Buddy, three things run on the Pi (each in its own
terminal, or as systemd services for auto-start on boot — a natural next step):

```bash
# 1. The brain (also serves Telegram + the API on :8642)
hermes gateway

# 2. The wake-word supervisor (launches the voice bot on the wake word)
cd ~/buddy && source .venv/bin/activate && python bot/wake_listener.py

# 3. The config web UI (:8080)
cd ~/buddy && source .venv/bin/activate && python config_server/server.py
```

### `.env.example` (the secrets template)

```bash
# Speech-to-text
DEEPGRAM_API_KEY=...

# Text-to-speech
CARTESIA_API_KEY=...
# CARTESIA_VOICE=71a7ad14-091c-4e8e-a314-022ece01c121

# Nous Hermes agent API server (must match API_SERVER_KEY in ~/.hermes/.env)
HERMES_URL=http://127.0.0.1:8642/v1
HERMES_API_KEY=change-me-local-dev

# Wake word — fully dynamic, change to anything and restart the listener
WAKE_WORD=hey buddy
VOSK_MODEL_PATH=~/buddy/models/vosk-small-en
BOT_IDLE_TIMEOUT=30
```

### The complete `index.html` (the web UI)

The front end is a single self-contained file. It is reproduced here in full for
completeness.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Buddy · Config</title>
<style>
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body {
    font-family: system-ui, -apple-system, sans-serif;
    max-width: 640px; margin: 0 auto; padding: 32px 20px;
    line-height: 1.5;
  }
  h1 { font-size: 1.6rem; margin: 0 0 4px; }
  .sub { opacity: 0.6; margin: 0 0 28px; font-size: 0.92rem; }
  label { display: block; font-weight: 600; margin: 22px 0 6px; }
  .hint { font-weight: 400; opacity: 0.6; font-size: 0.85rem; }
  input, textarea {
    width: 100%; padding: 10px 12px; font-size: 1rem;
    border: 1px solid color-mix(in srgb, currentColor 25%, transparent);
    border-radius: 8px; background: transparent; color: inherit;
    font-family: inherit;
  }
  textarea { min-height: 130px; resize: vertical; }
  button {
    margin-top: 24px; padding: 11px 22px; font-size: 1rem; font-weight: 600;
    border: none; border-radius: 8px; cursor: pointer;
    background: #2563eb; color: white;
  }
  button:disabled { opacity: 0.5; cursor: default; }
  #status {
    margin-top: 16px; padding: 12px 14px; border-radius: 8px;
    font-size: 0.9rem; display: none;
  }
  #status.ok  { display: block; background: color-mix(in srgb, #16a34a 18%, transparent); }
  #status.err { display: block; background: color-mix(in srgb, #dc2626 18%, transparent); }

  hr { border: none; border-top: 1px solid color-mix(in srgb, currentColor 15%, transparent); margin: 40px 0; }
  h2 { font-size: 1.2rem; margin: 0 0 4px; }
  .row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
  .row button { margin-top: 0; }
  .btn-secondary { background: transparent; border: 1px solid color-mix(in srgb, currentColor 30%, transparent); color: inherit; }
  .btn-danger { background: #dc2626; }
  .wifi-status { font-size: 0.9rem; padding: 10px 14px; border-radius: 8px;
    background: color-mix(in srgb, currentColor 8%, transparent); margin: 14px 0; }
  .net-list { margin: 12px 0; max-height: 220px; overflow-y: auto; }
  .net {
    display: flex; justify-content: space-between; padding: 9px 12px;
    border: 1px solid color-mix(in srgb, currentColor 12%, transparent);
    border-radius: 8px; margin-bottom: 6px; cursor: pointer;
  }
  .net:hover { background: color-mix(in srgb, currentColor 8%, transparent); }
  .net .meta { opacity: 0.6; font-size: 0.85rem; }
  #wifiStatus2 { margin-top: 14px; }
</style>
</head>
<body>
  <h1>🤖 Buddy · Configuration</h1>
  <p class="sub">Tune your companion. Changes save to the Pi and apply live.</p>

  <label for="wake">Wake word
    <span class="hint">— say this to start a conversation</span>
  </label>
  <input id="wake" type="text" placeholder="hey buddy" autocomplete="off">

  <label for="prompt">System prompt
    <span class="hint">— Buddy's personality &amp; instructions</span>
  </label>
  <textarea id="prompt" placeholder="You are Buddy..."></textarea>

  <label for="idle">Idle timeout (seconds)
    <span class="hint">— silence before a conversation ends</span>
  </label>
  <input id="idle" type="number" min="5" max="600" step="5">

  <button id="save">Save changes</button>
  <div id="status"></div>

  <hr>

  <h2>📶 Wi-Fi</h2>
  <p class="sub">Manage the Pi's network connection.</p>

  <div id="wifiStatus" class="wifi-status">Loading status…</div>

  <div class="row">
    <button id="scan" class="btn-secondary">Scan networks</button>
    <button id="radioOn" class="btn-secondary">Start Wi-Fi</button>
    <button id="radioOff" class="btn-danger">Stop Wi-Fi</button>
  </div>

  <div id="netList" class="net-list"></div>

  <label for="ssid">Network name (SSID)</label>
  <input id="ssid" type="text" autocomplete="off" placeholder="MyRouter_5G">

  <label for="wifipass">Password
    <span class="hint">— leave blank for open networks</span>
  </label>
  <input id="wifipass" type="password" autocomplete="off">

  <button id="connect">Connect</button>
  <div id="wifiStatus2" class="wifi-status" style="display:none"></div>

  <hr>

  <h2>🎧 Bluetooth</h2>
  <p class="sub">Pair a speaker or earphones for Buddy's voice.</p>

  <div id="btStatus" class="wifi-status">Loading status…</div>

  <div class="row">
    <button id="btScan" class="btn-secondary">Scan devices</button>
    <button id="btOn" class="btn-secondary">Turn on</button>
    <button id="btOff" class="btn-secondary">Turn off</button>
  </div>

  <div id="btList" class="net-list"></div>
  <div id="btMsg" class="wifi-status" style="display:none"></div>

<script>
const $ = (id) => document.getElementById(id);
const status = $("status");

function flash(msg, ok) {
  status.textContent = msg;
  status.className = ok ? "ok" : "err";
}

async function load() {
  try {
    const r = await fetch("/api/config");
    const c = await r.json();
    $("wake").value = c.wake_word ?? "";
    $("prompt").value = c.system_prompt ?? "";
    $("idle").value = c.idle_timeout ?? 30;
  } catch (e) {
    flash("Could not load config: " + e, false);
  }
}

$("save").addEventListener("click", async () => {
  const btn = $("save");
  btn.disabled = true;
  try {
    const r = await fetch("/api/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        wake_word: $("wake").value,
        system_prompt: $("prompt").value,
        idle_timeout: parseInt($("idle").value, 10),
      }),
    });
    const data = await r.json();
    if (data.ok) {
      $("wake").value = data.config.wake_word;
      $("idle").value = data.config.idle_timeout;
      flash("Saved. " + data.note, true);
    } else {
      flash("Save failed.", false);
    }
  } catch (e) {
    flash("Save failed: " + e, false);
  } finally {
    btn.disabled = false;
  }
});

// --- Wi-Fi ---------------------------------------------------------------
const wifiStatus = $("wifiStatus");
const wifiMsg = $("wifiStatus2");

function wflash(msg, ok) {
  wifiMsg.textContent = msg;
  wifiMsg.style.display = "block";
  wifiMsg.style.background = ok
    ? "color-mix(in srgb, #16a34a 18%, transparent)"
    : "color-mix(in srgb, #dc2626 18%, transparent)";
}

async function refreshWifi() {
  try {
    const s = await (await fetch("/api/wifi/status")).json();
    wifiStatus.innerHTML = s.enabled
      ? `Wi-Fi <b>on</b> · connected to <b>${s.active_ssid ?? "—"}</b> · IP ${s.ip ?? "—"}`
      : `Wi-Fi <b>off</b>`;
  } catch (e) {
    wifiStatus.textContent = "Could not read Wi-Fi status: " + e;
  }
}

$("scan").addEventListener("click", async () => {
  const list = $("netList");
  list.innerHTML = "<div class='meta'>Scanning…</div>";
  try {
    const r = await (await fetch("/api/wifi/scan")).json();
    if (!r.ok) { list.innerHTML = "<div class='meta'>Scan failed: " + r.error + "</div>"; return; }
    list.innerHTML = "";
    for (const n of r.networks) {
      const div = document.createElement("div");
      div.className = "net";
      const lock = n.security && n.security !== "open" ? "🔒" : "";
      div.innerHTML = `<span>${n.in_use ? "✓ " : ""}${n.ssid} ${lock}</span>`
                    + `<span class="meta">${n.signal}%</span>`;
      div.addEventListener("click", () => { $("ssid").value = n.ssid; $("wifipass").focus(); });
      list.appendChild(div);
    }
    if (!r.networks.length) list.innerHTML = "<div class='meta'>No networks found.</div>";
  } catch (e) {
    list.innerHTML = "<div class='meta'>Scan failed: " + e + "</div>";
  }
});

$("connect").addEventListener("click", async () => {
  const ssid = $("ssid").value.trim();
  if (!ssid) { wflash("Enter a network name first.", false); return; }
  if (!confirm(
    `Connect to "${ssid}"?\n\nIf this is a different network, the Pi may drop off `
    + `your current network and this page could stop responding. You'd then `
    + `reach Buddy at its new IP address.`
  )) return;
  wflash("Connecting… (this page may freeze if the Pi switches networks)", true);
  try {
    const r = await (await fetch("/api/wifi/connect", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ssid, password: $("wifipass").value || null }),
    })).json();
    wflash(r.ok ? "Connected: " + r.message : "Failed: " + r.message, r.ok);
    $("wifipass").value = "";
    refreshWifi();
  } catch (e) {
    wflash("No response — the Pi likely switched networks. Reconnect at its new IP.", false);
  }
});

$("radioOn").addEventListener("click", async () => {
  const r = await (await fetch("/api/wifi/radio", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled: true }),
  })).json();
  wflash(r.ok ? "Wi-Fi started." : "Failed: " + r.message, r.ok);
  refreshWifi();
});

$("radioOff").addEventListener("click", async () => {
  if (!confirm(
    "Stop Wi-Fi?\n\nIf you're reaching this page over Wi-Fi, you will LOSE access "
    + "and cannot turn it back on from here. Only do this with Ethernet or a "
    + "monitor+keyboard available on the Pi."
  )) return;
  try {
    const r = await (await fetch("/api/wifi/radio", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: false }),
    })).json();
    wflash(r.ok ? "Wi-Fi stopped." : "Failed: " + r.message, r.ok);
  } catch (e) {
    wflash("Wi-Fi stopped — this page is now disconnected.", false);
  }
});

// --- Bluetooth -----------------------------------------------------------
const btStatus = $("btStatus");
const btMsg = $("btMsg");

function btflash(msg, ok) {
  btMsg.textContent = msg;
  btMsg.style.display = "block";
  btMsg.style.background = ok
    ? "color-mix(in srgb, #16a34a 18%, transparent)"
    : "color-mix(in srgb, #dc2626 18%, transparent)";
}

function renderBt(data) {
  btStatus.innerHTML = data.powered ? "Bluetooth <b>on</b>" : "Bluetooth <b>off</b>";
  const list = $("btList");
  list.innerHTML = "";
  for (const d of (data.devices || [])) {
    const div = document.createElement("div");
    div.className = "net";
    const tag = d.connected ? "✓ connected" : (d.paired ? "paired" : "");
    const btn = d.connected ? "Disconnect" : "Connect";
    div.innerHTML = `<span>${d.name} <span class="meta">${d.mac} ${tag}</span></span>`;
    const b = document.createElement("button");
    b.textContent = btn;
    b.className = "btn-secondary";
    b.style.marginTop = "0";
    b.style.padding = "5px 12px";
    b.addEventListener("click", async (e) => {
      e.stopPropagation();
      b.disabled = true; b.textContent = "…";
      const path = d.connected ? "/api/bt/disconnect" : "/api/bt/connect";
      try {
        const r = await (await fetch(path, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ mac: d.mac }),
        })).json();
        btflash((d.connected ? "Disconnect" : "Connect") + ": " + r.message, r.ok);
      } catch (err) {
        btflash("Failed: " + err, false);
      } finally {
        refreshBt();
      }
    });
    div.appendChild(b);
    list.appendChild(div);
  }
  if (!(data.devices || []).length) list.innerHTML = "<div class='meta'>No devices yet — try Scan.</div>";
}

async function refreshBt() {
  try { renderBt(await (await fetch("/api/bt/devices")).json()); }
  catch (e) { btStatus.textContent = "Could not read Bluetooth: " + e; }
}

$("btScan").addEventListener("click", async () => {
  $("btList").innerHTML = "<div class='meta'>Scanning ~8s…</div>";
  try { renderBt(await (await fetch("/api/bt/scan")).json()); }
  catch (e) { btflash("Scan failed: " + e, false); }
});

$("btOn").addEventListener("click", async () => {
  const r = await (await fetch("/api/bt/power", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled: true }),
  })).json();
  btflash(r.ok ? "Bluetooth on." : "Failed: " + r.message, r.ok);
  refreshBt();
});

$("btOff").addEventListener("click", async () => {
  if (!confirm("Turn Bluetooth off? Buddy's earphones/speaker will disconnect.")) return;
  const r = await (await fetch("/api/bt/power", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled: false }),
  })).json();
  btflash(r.ok ? "Bluetooth off." : "Failed: " + r.message, r.ok);
  refreshBt();
});

load();
refreshWifi();
refreshBt();
</script>
</body>
</html>
```

---

## Closing

From a bare circuit board to a talking companion: we flashed an OS, fought the
Wi-Fi country code (twice), installed a real autonomous AI agent and exposed it
over an OpenAI-compatible API, built a streaming voice pipeline around it,
engineered the audio stack into working with Bluetooth, added a dynamic wake word
with a clean supervisor architecture, built a web UI to configure it all
(including Wi-Fi and Bluetooth management), connected it to Telegram, made it
reachable from the internet, and packaged the whole thing as a reusable skill.

Every component is decoupled and swappable: change the STT or TTS provider in one
line, point the LLM at a different OpenAI-compatible endpoint, set any wake word
from a web form. The architecture's throughline is the OpenAI-compatible API
boundary, which let the voice layer and the agent layer evolve independently.

The natural next step, whenever it's wanted: systemd services so the gateway, wake
listener, and config server all start automatically on boot — turning Buddy from a
project you launch over SSH into a true appliance that just works when powered on.

