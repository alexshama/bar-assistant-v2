"""
Обработчики команд /start, /help, /mode, /reset, /stats, /reindex
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from rag.index import rebuild_index

logger = logging.getLogger(__name__)
router = Router()

# Хранилище пользовательских настроек
user_settings = {}


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start"""
    welcome_text = """
🍸 <b>Добро пожаловать в Барный ассистент!</b>

Я помогу вам с:
• 🍹 Рецептами коктейлей и их приготовлением
• 🍺 Информацией о пиве и его стилях  
• 🥃 Знаниями об алкогольных напитках
• 🖼 Генерацией изображений коктейлей
• 🎤 Голосовыми запросами (отправьте голосовое сообщение)

<b>Команды:</b>
/help - примеры вопросов
/mode - переключение режима ответа
/voice - включить/выключить озвучку
/reset - сброс контекста
/stats - статистика
/reindex - переиндексация базы знаний

Просто задайте вопрос или попросите рецепт!
    """
    
    await message.answer(welcome_text)


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help"""
    help_text = """
<b>Примеры вопросов:</b>

🍹 <b>Рецепты коктейлей:</b>
• "Рецепт Негрони"
• "Как приготовить Мохито?"
• "Покажи картинку Маргариты"

🍺 <b>Пиво:</b>
• "Чем отличается IPA от лагера?"
• "Какое пиво подать к стейку?"

🥃 <b>Алкоголь:</b>
• "Разница между виски и бурбоном"
• "Какой джин лучше для мартини?"

🎤 <b>Голосовые запросы:</b>
Отправьте голосовое сообщение с вопросом

🖼 <b>Изображения:</b>
• "Сгенерируй картинку Космополитена"
• "Покажи как подавать Олд Фэшн"

⚙️ <b>Административные команды:</b>
• /cache_stats - статистика кэша изображений
• /clear_cache - очистить кэш (только админ)

💾 <i>Изображения кэшируются для экономии API вызовов!</i>
    """
    
    await message.answer(help_text)


@router.message(Command("mode"))
async def cmd_mode(message: Message):
    """Переключение режима ответа"""
    user_id = message.from_user.id
    
    if user_id not in user_settings:
        user_settings[user_id] = {"mode": "подробно", "voice_enabled": False}
    
    current_mode = user_settings[user_id]["mode"]
    new_mode = "кратко" if current_mode == "подробно" else "подробно"
    user_settings[user_id]["mode"] = new_mode
    
    await message.answer(f"Режим ответа изменен на: <b>{new_mode}</b>")


@router.message(Command("voice"))
async def cmd_voice(message: Message):
    """Включение/выключение озвучки"""
    user_id = message.from_user.id
    
    if user_id not in user_settings:
        user_settings[user_id] = {"mode": "подробно", "voice_enabled": False}
    
    # Парсим аргумент команды
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if args and args[0].lower() in ["on", "вкл", "включить"]:
        user_settings[user_id]["voice_enabled"] = True
        await message.answer("🔊 Озвучка ответов <b>включена</b>")
    elif args and args[0].lower() in ["off", "выкл", "выключить"]:
        user_settings[user_id]["voice_enabled"] = False
        await message.answer("🔇 Озвучка ответов <b>выключена</b>")
    else:
        current_status = "включена" if user_settings[user_id]["voice_enabled"] else "выключена"
        await message.answer(
            f"Озвучка сейчас <b>{current_status}</b>\n\n"
            f"Использование:\n"
            f"/voice on - включить\n"
            f"/voice off - выключить"
        )


@router.message(Command("reset"))
async def cmd_reset(message: Message, state: FSMContext):
    """Сброс контекста сессии"""
    await state.clear()
    user_id = message.from_user.id
    
    if user_id in user_settings:
        user_settings[user_id] = {"mode": "подробно", "voice_enabled": False}
    
    await message.answer("🔄 Контекст сессии сброшен")


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Статистика бота"""
    # Здесь можно добавить реальную статистику
    stats_text = """
📊 <b>Статистика:</b>

• Запросов обработано: 42
• Среднее время ответа: 1.2 сек
• База знаний: 156 документов
• Активных пользователей: 8

🤖 Бот работает стабильно
    """
    
    await message.answer(stats_text)


@router.message(Command("reindex"))
async def cmd_reindex(message: Message):
    """Переиндексация RAG базы знаний"""
    try:
        await message.answer("🔄 Начинаю переиндексацию базы знаний...")
        
        # Запускаем переиндексацию
        result = await rebuild_index()
        
        if result["success"]:
            await message.answer(
                f"✅ Переиндексация завершена!\n\n"
                f"📄 Обработано документов: {result['documents_count']}\n"
                f"📝 Создано чанков: {result['chunks_count']}"
            )
        else:
            await message.answer(f"❌ Ошибка переиндексации: {result['error']}")
            
    except Exception as e:
        logger.error(f"Ошибка при переиндексации: {e}")
        await message.answer("❌ Произошла ошибка при переиндексации")


def get_user_settings(user_id: int) -> dict:
    """Получить настройки пользователя"""
    if user_id not in user_settings:
        user_settings[user_id] = {"mode": "подробно", "voice_enabled": False}
    return user_settings[user_id]