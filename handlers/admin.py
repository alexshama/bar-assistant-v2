"""
Administrative command handlers.
"""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import settings
from services.image_cache import image_cache

logger = logging.getLogger(__name__)
router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_user_ids


@router.message(Command("cache_stats"))
async def handle_cache_stats(message: Message) -> None:
    try:
        stats = image_cache.get_cache_stats()
        if "error" in stats:
            await message.answer(f"❌ Не удалось получить статистику кэша: {stats['error']}")
            return

        response = (
            "📊 <b>Статистика кэша изображений</b>\n\n"
            f"📁 Файлов: {stats['total_files']}\n"
            f"💾 Размер: {stats['total_size_mb']} МБ\n"
            f"📂 Папка: {stats['cache_dir']}"
        )
        await message.answer(response, parse_mode="HTML")
    except Exception:
        logger.exception("Failed to get cache stats.")
        await message.answer("❌ Произошла ошибка при получении статистики кэша.")


@router.message(Command("clear_cache"))
async def handle_clear_cache(message: Message) -> None:
    try:
        if not settings.admin_user_ids:
            await message.answer(
                "❌ Команда отключена: в `.env` не указаны `ADMIN_USER_IDS`."
            )
            return

        if not _is_admin(message.from_user.id):
            await message.answer("❌ У вас нет прав для выполнения этой команды.")
            return

        cleared_count = image_cache.clear_cache()
        await message.answer(
            "🗑 <b>Кэш очищен</b>\n\n"
            f"Удалено файлов: {cleared_count}",
            parse_mode="HTML",
        )
    except Exception:
        logger.exception("Failed to clear image cache.")
        await message.answer("❌ Произошла ошибка при очистке кэша.")
