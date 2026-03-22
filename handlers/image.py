"""
Image message handler.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import Message

from handlers.start import get_user_settings
from services.router import process_text_request
from services.runtime_stats import runtime_stats
from services.vision import analyze_image

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.photo)
async def handle_photo_message(message: Message) -> None:
    try:
        user_id = message.from_user.id
        runtime_stats.mark_image()
        logger.info("Received image from user %s", user_id)

        await message.bot.send_chat_action(message.chat.id, "typing")

        photo = message.photo[-1]
        photo_file = await message.bot.get_file(photo.file_id)
        photo_bytes = await message.bot.download_file(photo_file.file_path)

        caption = (
            message.caption
            or "Что изображено на этой фотографии? Это напиток или коктейль?"
        )

        analysis_result = await analyze_image(
            image_bytes=photo_bytes.read(),
            prompt=f"Проанализируй это изображение как бармен-эксперт: {caption}",
        )

        if not analysis_result:
            await message.answer("😔 Не удалось проанализировать изображение. Попробуйте еще раз.")
            return

        await message.answer(
            f"🔎 <b>Анализ изображения:</b>\n\n{analysis_result}",
            parse_mode="HTML",
        )

        if "коктейль" not in analysis_result.lower() and "напиток" not in analysis_result.lower():
            return

        preferences = get_user_settings(user_id)
        follow_up_query = f"Расскажи подробнее про {analysis_result[:100]}"
        follow_up_response = await process_text_request(
            text=follow_up_query,
            user_id=user_id,
            mode=preferences["mode"],
        )

        if follow_up_response.get("text"):
            await message.answer(
                f"📚 <b>Дополнительная информация:</b>\n\n{follow_up_response['text']}",
                parse_mode="HTML",
            )
    except Exception:
        runtime_stats.mark_failed()
        logger.exception("Failed to handle photo message.")
        await message.answer(
            "😔 Произошла ошибка при анализе изображения. Попробуйте еще раз позже."
        )
