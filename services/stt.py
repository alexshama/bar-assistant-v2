"""
Speech-to-text service helpers.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

import aiohttp

from config import settings
from services.openai_client import openai_client

logger = logging.getLogger(__name__)


async def transcribe_voice_message(ogg_path: str) -> Optional[str]:
    wav_path: str | None = None

    try:
        if not os.path.exists(ogg_path):
            logger.error("Audio file does not exist: %s", ogg_path)
            return None

        wav_path = await _convert_ogg_to_wav(ogg_path)
        if not wav_path:
            return None

        transcription = await _try_openrouter_stt(wav_path)
        if transcription:
            return transcription.strip()

        transcription = await openai_client.stt(wav_path)
        return transcription.strip() if transcription else None
    except Exception as error:
        logger.error("Voice transcription failed: %s", error)
        return None
    finally:
        if wav_path and wav_path != ogg_path and os.path.exists(wav_path):
            try:
                os.unlink(wav_path)
            except OSError:
                logger.warning("Could not remove temporary WAV file: %s", wav_path)


async def _try_openrouter_stt(audio_path: str) -> Optional[str]:
    try:
        suffix = Path(audio_path).suffix.lower()
        content_type = "audio/wav" if suffix == ".wav" else "audio/ogg"

        with open(audio_path, "rb") as audio_file:
            audio_data = audio_file.read()

        data = aiohttp.FormData()
        data.add_field("file", audio_data, filename=f"audio{suffix or '.ogg'}", content_type=content_type)
        data.add_field("model", "openai/whisper-large-v3")
        data.add_field("language", "ru")

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=settings.request_timeout_seconds)) as session:
            async with session.post(
                "https://openrouter.ai/api/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
                data=data,
            ) as response:
                if response.status != 200:
                    logger.warning("OpenRouter STT returned status %s", response.status)
                    return None

                result = await response.json()
                text = result.get("text", "")
                return text.strip() or None
    except Exception as error:
        logger.warning("OpenRouter STT failed: %s", error)
        return None


async def _convert_ogg_to_wav(ogg_path: str) -> Optional[str]:
    try:
        from pydub import AudioSegment

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            wav_path = temp_file.name

        audio = AudioSegment.from_ogg(ogg_path)
        audio.export(wav_path, format="wav")
        return wav_path
    except ImportError as error:
        logger.info("pydub is unavailable, using original audio file: %s", error)
        return ogg_path if os.path.exists(ogg_path) else None
    except Exception as error:
        logger.warning("OGG to WAV conversion failed: %s", error)
        return None
