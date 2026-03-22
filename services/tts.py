"""
Text-to-speech helpers.
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Optional

from aiogram.types import FSInputFile, Message

from services.openai_client import openai_client

logger = logging.getLogger(__name__)


async def send_voice_response(message: Message, text: str, voice: str = "alloy") -> bool:
    temp_path: str | None = None

    try:
        audio_bytes = await openai_client.tts(text, voice)
        if not audio_bytes:
            return False

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(audio_bytes)

        await message.answer_voice(FSInputFile(temp_path))
        return True
    except Exception as error:
        logger.error("Failed to send voice response: %s", error)
        return False
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                logger.warning("Could not remove temporary TTS file: %s", temp_path)


async def synthesize_speech(text: str, voice: str = "alloy") -> Optional[bytes]:
    try:
        return await openai_client.tts(text, voice)
    except Exception as error:
        logger.error("Speech synthesis failed: %s", error)
        return None
