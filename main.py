#!/usr/bin/env python3
"""
Application entrypoint for the Telegram bot.
"""

from __future__ import annotations

import asyncio
import logging

from bootstrap import initialize_application
from bot import create_bot
from services.utils import configure_logging

configure_logging()
logger = logging.getLogger(__name__)


async def main() -> None:
    try:
        logger.info("Starting Telegram bot 'Барный ассистент'...")

        await initialize_application()
        bot, dp = create_bot()

        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception:
        logger.exception("Failed to start Telegram bot.")
        raise


if __name__ == "__main__":
    asyncio.run(main())
