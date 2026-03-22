"""
Text message handler.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import Message

from handlers.start import get_user_settings
from services.router import process_text_request
from services.runtime_stats import runtime_stats
from services.telegram_helpers import send_response_payload

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text)
async def handle_text_message(message: Message) -> None:
    try:
        user_id = message.from_user.id
        user_text = (message.text or "").strip()

        if not user_text:
            await message.answer("Напишите запрос текстом, и я помогу.")
            return

        runtime_stats.mark_text()
        logger.info("Received text request from %s: %s", user_id, user_text[:120])

        await message.bot.send_chat_action(message.chat.id, "typing")

        preferences = get_user_settings(user_id)
        response = await process_text_request(
            text=user_text,
            user_id=user_id,
            mode=preferences["mode"],
        )

        await send_response_payload(
            message=message,
            response=response,
            send_voice=preferences["voice_enabled"],
        )
    except Exception:
        runtime_stats.mark_failed()
        logger.exception("Failed to handle text message.")
        await message.answer(
            "😔 Не удалось обработать текстовый запрос. Попробуйте еще раз через несколько секунд."
        )
