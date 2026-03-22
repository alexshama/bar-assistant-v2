"""
Helpers for sending Telegram responses without duplicating handler logic.
"""

from __future__ import annotations

import logging
from typing import Any

from aiogram.types import BufferedInputFile, Message

from services.tts import send_voice_response

logger = logging.getLogger(__name__)


def build_cocktail_caption(response: dict[str, Any]) -> str:
    cocktail_name = "коктейля"

    for source in response.get("sources", []):
        chunk_id = source.get("chunk_id", "")
        if "COCKTAIL" not in chunk_id.upper():
            continue

        parts = chunk_id.split("_")
        if len(parts) < 3:
            continue

        name_part = "_".join(parts[2:])
        cocktail_name = name_part.replace("_", " ").title()
        cocktail_name = {
            "Long Island Iced Tea": "Long Island Iced Tea",
            "B 52": "B-52",
            "Old Fashioned": "Old Fashioned",
            "Espresso Martini": "Espresso Martini",
        }.get(cocktail_name, cocktail_name)
        break

    return f"🖼 Изображение {cocktail_name}"


async def send_response_payload(
    message: Message,
    response: dict[str, Any],
    *,
    send_voice: bool = False,
) -> None:
    await message.answer(response["text"], parse_mode="HTML")

    if response.get("image_bytes"):
        photo = BufferedInputFile(response["image_bytes"], filename="cocktail_image.png")
        await message.answer_photo(photo=photo, caption=build_cocktail_caption(response))

    if send_voice and response.get("tts_text"):
        tts_sent = await send_voice_response(message=message, text=response["tts_text"])
        if not tts_sent:
            logger.warning("Voice response could not be sent to user %s", message.from_user.id)
