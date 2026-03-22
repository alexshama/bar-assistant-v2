"""
Bot factory and router registration.
"""

from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from handlers import admin, image, start, text, voice

logger = logging.getLogger(__name__)


def create_bot() -> tuple[Bot, Dispatcher]:
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dispatcher = Dispatcher()
    dispatcher.include_router(start.router)
    dispatcher.include_router(admin.router)
    dispatcher.include_router(text.router)
    dispatcher.include_router(voice.router)
    dispatcher.include_router(image.router)

    logger.info("Bot and dispatcher are configured.")
    return bot, dispatcher
