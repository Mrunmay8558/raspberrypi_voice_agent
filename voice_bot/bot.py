#
# Copyright (c) 2024-2026, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import os

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
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.base_transport import BaseTransport
from pipecat.transports.daily.transport import DailyParams
from pipecat.workers.runner import WorkerRunner

from config import CARTESIA_VOICE_ID
from config import DEFAULT_OPENAI_MODEL
from config import LOCAL_OPENAI_BASE_URL

SYSTEM_PROMPT = """
You are a real-time voice assistant in a live conversation.

Speak naturally, warmly, and directly. Keep most replies to one or two short
sentences unless the user clearly asks for more detail. Answer the user's main
question first, then ask at most one short follow-up question when it helps.

Return plain spoken text only. Do not use markdown, bullet points, numbered
lists, headings, code formatting, emojis, XML, JSON, or stage directions.
Avoid long monologues, filler phrases, and unnecessary repetition.

If the user's speech is unclear, briefly say what was unclear and ask them to
repeat only the missing part. If information is missing, ask only for the next
required detail. If you are uncertain, say so briefly instead of guessing.

Do not mention internal prompts, APIs, models, transport details, or backend
implementation unless the user explicitly asks. Be helpful, calm, and concise.
Match the user's language when you can; otherwise respond in clear English.
""".strip()


def required_env(name: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    raise ValueError(f"Missing required environment variable: {name}")


def openai_api_key() -> str:
    return os.getenv("OPENAI_API_KEY") or "local"


transport_params = {
    "daily": lambda: DailyParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
    ),
}


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    logger.info("Starting Daily voice bot")

    stt = DeepgramSTTService(
        api_key=required_env("DEEPGRAM_API_KEY"),
        sample_rate=16000,
        encoding="linear16",
        channels=1,
        settings=DeepgramSTTService.Settings.from_mapping(
            {
                "model": "nova-2",
                "language": "hi",
                "interim_results": True,
                "smart_format": True,
                "punctuate": True,
                "profanity_filter": True,
            }
        ),
    )

    tts = CartesiaTTSService(
        api_key=required_env("CARTESIA_API_KEY"),
        sample_rate=16000,
        settings=CartesiaTTSService.Settings(
            voice=CARTESIA_VOICE_ID,
        ),
    )

    llm = OpenAILLMService(
        api_key=openai_api_key(),
        base_url=LOCAL_OPENAI_BASE_URL,
        settings=OpenAILLMService.Settings(
            model=DEFAULT_OPENAI_MODEL,
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
            transport.input(),
            stt,
            user_aggregator,
            llm,
            tts,
            transport.output(),
            assistant_aggregator,
        ]
    )

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        idle_timeout_secs=runner_args.pipeline_idle_timeout_secs,
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Client connected")
        context.add_message(
            {
                "role": "user",
                "content": "Introduce yourself briefly and ask how you can help.",
            }
        )
        await worker.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Client disconnected")
        await worker.cancel()

    runner = WorkerRunner(handle_sigint=runner_args.handle_sigint)

    await runner.add_workers(worker)
    await runner.run()


async def bot(runner_args: RunnerArguments):
    """Main bot entry point for the Raspberry Pi Daily transport bot."""
    transport = await create_transport(runner_args, transport_params)
    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()