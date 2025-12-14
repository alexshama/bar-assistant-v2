#!/usr/bin/env python3
"""
Telegram Bot "Барный ассистент"
Точка входа в приложение
"""

import asyncio
import logging
from bot import create_bot
from config import settings

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """Основная функция запуска бота"""
    try:
        logger.info("Запуск Telegram бота 'Барный ассистент'...")
        
        # Создаем и запускаем бота
        bot, dp = create_bot()
        
        # Удаляем webhook и запускаем polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())