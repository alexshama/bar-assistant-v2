"""
Основная логика Telegram бота
"""

import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from handlers import start, text, voice, image, admin

logger = logging.getLogger(__name__)


def create_bot() -> tuple[Bot, Dispatcher]:
    """Создание и настройка бота"""
    
    # Создаем бота
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Создаем диспетчер
    dp = Dispatcher()
    
    # Регистрируем роутеры
    dp.include_router(start.router)
    dp.include_router(admin.router)  # Административные команды
    dp.include_router(text.router)
    dp.include_router(voice.router)
    dp.include_router(image.router)
    
    logger.info("Бот создан и настроен")
    
    return bot, dp