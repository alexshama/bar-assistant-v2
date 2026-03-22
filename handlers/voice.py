"""
Voice message handler.
"""

from __future__ import annotations

import logging
import os
import tempfile

from aiogram import F, Router
from aiogram.types import Message

from handlers.start import get_user_settings
from services.router import process_text_request
from services.runtime_stats import runtime_stats
from services.stt import transcribe_voice_message
from services.telegram_helpers import send_response_payload

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.voice)
async def handle_voice_message(message: Message) -> None:
    temp_path: str | None = None

    try:
        user_id = message.from_user.id
        runtime_stats.mark_voice()
        logger.info("Received voice request from %s", user_id)

        await message.bot.send_chat_action(message.chat.id, "typing")

        voice_file = await message.bot.get_file(message.voice.file_id)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
            temp_path = temp_file.name

        await message.bot.download_file(voice_file.file_path, temp_path)
        transcription = await transcribe_voice_message(temp_path)

        if not transcription:
            await message.answer(
                "😔 Не удалось распознать речь. Попробуйте еще раз или отправьте вопрос текстом."
            )
            return

        await message.answer(f"🎤 Распознано: <i>{transcription}</i>", parse_mode="HTML")

        preferences = get_user_settings(user_id)
        response = await process_text_request(
            text=transcription,
            user_id=user_id,
            mode=preferences["mode"],
        )

        await send_response_payload(message=message, response=response, send_voice=True)
    except Exception:
        runtime_stats.mark_failed()
        logger.exception("Failed to handle voice message.")
        await message.answer(
            "😔 Не удалось обработать голосовое сообщение. Попробуйте еще раз или напишите текстом."
        )
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                logger.warning("Temporary voice file could not be removed: %s", temp_path)
