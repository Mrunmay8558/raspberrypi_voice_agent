import os
import argparse
import asyncio

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
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.base_transport import BaseTransport
from pipecat.transports.local.audio import LocalAudioTransport
from pipecat.transports.local.audio import LocalAudioTransportParams
from pipecat.workers.runner import WorkerRunner

from config import CARTESIA_VOICE_ID
from config import DEFAULT_OPENAI_MODEL
from config import LOCAL_OPENAI_BASE_URL
from config import SAMPLE_RATE

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


def create_bot_transport() -> BaseTransport:
    return LocalAudioTransport(
        LocalAudioTransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            audio_in_sample_rate=SAMPLE_RATE,
            audio_out_sample_rate=SAMPLE_RATE,
            audio_in_channels=1,
            audio_out_channels=1,
        )
    )


async def run_bot(
    transport: BaseTransport,
    *,
    pipeline_idle_timeout_secs: int = 300,
    handle_sigint: bool = True,
):
    logger.info("Starting voice bot")

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
        idle_timeout_secs=pipeline_idle_timeout_secs,
    )

    async def start_conversation():
        context.add_message(
            {
                "role": "user",
                "content": "Introduce yourself briefly and ask how you can help.",
            }
        )
        await worker.queue_frames([LLMRunFrame()])

    runner = WorkerRunner(handle_sigint=handle_sigint, handle_sigterm=True)

    @runner.event_handler("on_ready")
    async def on_runner_ready():
        logger.info("Local audio transport ready")
        await start_conversation()

    await runner.add_workers(worker)
    await runner.run()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Raspberry Pi voice bot directly on local audio devices."
    )
    parser.add_argument(
        "--pipeline-idle-timeout-secs",
        type=int,
        default=300,
        help="Seconds the local audio pipeline may stay idle before shutting down.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    transport = create_bot_transport()
    await run_bot(
        transport,
        pipeline_idle_timeout_secs=args.pipeline_idle_timeout_secs,
    )


if __name__ == "__main__":
    asyncio.run(main())
