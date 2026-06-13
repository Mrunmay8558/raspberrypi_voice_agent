import argparse
import asyncio
import os
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from loguru import logger

from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import (
    EndFrame,
    LLMMessagesAppendFrame,
    TTSSpeakFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.llm_service import FunctionCallParams
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
You are running on a Raspberry Pi voice assistant using local microphone and
speaker audio.

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

When the user says they are done, wants to stop, says goodbye, asks to end the
call, or otherwise clearly wants to finish the session, call the `end_call`
tool instead of continuing the conversation.
""".strip()


INTRODUCTION_PROMPT = "Please introduce yourself briefly and ask how you can help."


class UserIdleHandler:
    """Manage conversational idle prompts before ending a local audio session."""

    def __init__(self, *, max_prompts: int = 3):
        self._idle_count = 0
        self._max_prompts = max_prompts

    def reset(self) -> None:
        self._idle_count = 0

    async def handle_idle(self, aggregator) -> None:
        self._idle_count += 1

        if self._idle_count == 1:
            await aggregator.push_frame(
                LLMMessagesAppendFrame(
                    [
                        {
                            "role": "user",
                            "content": (
                                "The user has been quiet. Briefly ask if they "
                                "are still there."
                            ),
                        }
                    ],
                    run_llm=True,
                )
            )
            return

        if self._idle_count < self._max_prompts:
            await aggregator.push_frame(
                TTSSpeakFrame(
                    "Are you still there? I can keep going if you want to continue."
                )
            )
            return

        await aggregator.push_frame(
            TTSSpeakFrame(
                "I will stop listening for now. Say the wake word when you need me."
            )
        )
        await aggregator.push_frame(EndFrame())


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


async def end_call(params: FunctionCallParams) -> None:
    """End the current voice session.

    Use this when the user says they are done, says goodbye, asks to stop,
    or asks to end the call/session.
    """
    logger.info("Ending voice session through end_call tool")
    await params.result_callback({"status": "ending"})
    await params.pipeline_worker.queue_frames(
        [
            TTSSpeakFrame("Okay, I will stop here. Say the wake word when you need me."),
            EndFrame(),
        ]
    )


async def run_bot(
    transport: BaseTransport,
    *,
    pipeline_idle_timeout_secs: int = 300,
    user_idle_timeout_secs: float = 20.0,
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
    llm.register_direct_function(end_call)

    context = LLMContext(tools=ToolsSchema(standard_tools=[end_call]))
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            user_idle_timeout=user_idle_timeout_secs,
            vad_analyzer=SileroVADAnalyzer(),
        ),
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

    idle_handler = UserIdleHandler()

    @user_aggregator.event_handler("on_user_turn_idle")
    async def on_user_turn_idle(aggregator):
        logger.info("User turn idle")
        await idle_handler.handle_idle(aggregator)

    @user_aggregator.event_handler("on_user_turn_started")
    async def on_user_turn_started(_aggregator, _strategy):
        idle_handler.reset()

    runner = WorkerRunner(handle_sigint=handle_sigint, handle_sigterm=True)

    @runner.event_handler("on_ready")
    async def on_runner_ready(_runner):
        logger.info("Local audio transport ready")
        await worker.queue_frame(
            LLMMessagesAppendFrame(
                [
                    {
                        "role": "user",
                        "content": INTRODUCTION_PROMPT,
                    }
                ],
                run_llm=True,
            )
        )

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
        help="Seconds the pipeline worker may stay idle before process cleanup.",
    )
    parser.add_argument(
        "--user-idle-timeout-secs",
        type=float,
        default=20.0,
        help="Seconds of user silence before the assistant prompts the user.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    transport = create_bot_transport()
    await run_bot(
        transport,
        pipeline_idle_timeout_secs=args.pipeline_idle_timeout_secs,
        user_idle_timeout_secs=args.user_idle_timeout_secs,
    )


if __name__ == "__main__":
    asyncio.run(main())
