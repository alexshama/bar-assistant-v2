"""
Административные команды для бота
"""

import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from services.image_cache import image_cache

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("cache_stats"))
async def handle_cache_stats(message: Message):
    """Показать статистику кэша изображений"""
    try:
        user_id = message.from_user.id
        logger.info(f"Запрос статистики кэша от пользователя {user_id}")
        
        # Получаем статистику кэша
        stats = image_cache.get_cache_stats()
        
        if "error" in stats:
            await message.answer(f"❌ Ошибка при получении статистики: {stats['error']}")
            return
        
        # Формируем ответ
        response = (
            f"📊 <b>Статистика кэша изображений:</b>\n\n"
            f"📁 Всего файлов: {stats['total_files']}\n"
            f"💾 Размер: {stats['total_size_mb']} МБ\n"
            f"📂 Папка: {stats['cache_dir']}\n\n"
            f"💰 <i>Кэш помогает экономить деньги на повторной генерации изображений!</i>"
        )
        
        await message.answer(response, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке команды cache_stats: {e}")
        await message.answer("❌ Произошла ошибка при получении статистики кэша.")


@router.message(Command("clear_cache"))
async def handle_clear_cache(message: Message):
    """Очистить кэш изображений (только для администраторов)"""
    try:
        user_id = message.from_user.id
        
        # Простая проверка на администратора (можно расширить)
        admin_ids = [1474064316]  # Добавьте свой user_id
        
        if user_id not in admin_ids:
            await message.answer("❌ У вас нет прав для выполнения этой команды.")
            return
        
        logger.info(f"Очистка кэша по запросу администратора {user_id}")
        
        # Очищаем кэш
        cleared_count = image_cache.clear_cache()
        
        await message.answer(
            f"🗑 <b>Кэш очищен!</b>\n\n"
            f"Удалено файлов: {cleared_count}",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при очистке кэша: {e}")
        await message.answer("❌ Произошла ошибка при очистке кэша.")