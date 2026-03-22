"""
Handlers for user-facing commands.
"""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from rag.index import rebuild_index
from rag.query import get_knowledge_stats
from services.image_cache import image_cache
from services.runtime_stats import runtime_stats
from services.user_preferences import user_preferences_store

logger = logging.getLogger(__name__)
router = Router()


WELCOME_TEXT = """
🍸 <b>Добро пожаловать в Барный ассистент v2</b>

Я помогаю с:
• рецептами коктейлей и подачей;
• теорией по алкоголю, пиву и стилям;
• рекомендациями и заменами ингредиентов;
• генерацией изображений коктейлей;
• голосовыми запросами.

<b>Команды:</b>
/help - примеры запросов
/mode - переключить подробный/краткий режим
/voice - включить или отключить озвучку
/reset - сбросить контекст и настройки сессии
/stats - показать runtime-статистику
/reindex - переиндексировать базу знаний
""".strip()


HELP_TEXT = """
<b>Примеры запросов</b>

🍹 <b>Рецепты</b>
• Рецепт Негрони
• Как приготовить Мохито?
• Покажи фото Маргариты

🥃 <b>Напитки и теория</b>
• Что такое виски?
• Чем отличается IPA от лагера?
• Как правильно подавать коктейль?

💡 <b>Рекомендации</b>
• Какой виски лучше предложить вместо бурбона?
• Посоветуй коктейль с джином

🎤 <b>Голос</b>
Отправьте голосовое сообщение с любым вопросом.

🛠 <b>Админ-команды</b>
• /cache_stats
• /clear_cache
""".strip()


def get_user_settings(user_id: int) -> dict:
    return user_preferences_store.get(user_id)


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME_TEXT)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command("mode"))
async def cmd_mode(message: Message) -> None:
    user_id = message.from_user.id
    current = user_preferences_store.get(user_id)
    new_mode = "кратко" if current["mode"] == "подробно" else "подробно"
    user_preferences_store.update(user_id, mode=new_mode)
    await message.answer(f"Режим ответа изменен на: <b>{new_mode}</b>")


@router.message(Command("voice"))
async def cmd_voice(message: Message) -> None:
    user_id = message.from_user.id
    current = user_preferences_store.get(user_id)
    args = message.text.split()[1:] if message.text else []

    if args and args[0].lower() in {"on", "вкл", "включить"}:
        user_preferences_store.update(user_id, voice_enabled=True)
        await message.answer("🔊 Озвучка ответов <b>включена</b>")
        return

    if args and args[0].lower() in {"off", "выкл", "выключить"}:
        user_preferences_store.update(user_id, voice_enabled=False)
        await message.answer("🔇 Озвучка ответов <b>выключена</b>")
        return

    current_status = "включена" if current["voice_enabled"] else "выключена"
    await message.answer(
        f"Озвучка сейчас <b>{current_status}</b>\n\n"
        "Использование:\n"
        "/voice on - включить\n"
        "/voice off - выключить"
    )


@router.message(Command("reset"))
async def cmd_reset(message: Message, state: FSMContext) -> None:
    await state.clear()
    user_preferences_store.reset(message.from_user.id)
    await message.answer("🔄 Контекст сессии и настройки ответа сброшены.")


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    knowledge_stats = get_knowledge_stats()
    cache_stats = image_cache.get_cache_stats()
    total_docs = knowledge_stats.get("total_documents", 0)
    active_users = user_preferences_store.count_users()
    cache_files = cache_stats.get("total_files", 0) if "error" not in cache_stats else 0

    stats_text = (
        "📊 <b>Runtime-статистика</b>\n\n"
        f"• Аптайм: {runtime_stats.uptime_seconds()} сек\n"
        f"• Всего запросов: {runtime_stats.total_requests}\n"
        f"• Текстовых: {runtime_stats.text_requests}\n"
        f"• Голосовых: {runtime_stats.voice_requests}\n"
        f"• Запросов по фото: {runtime_stats.image_requests}\n"
        f"• Ошибок: {runtime_stats.failed_requests}\n"
        f"• Документов в индексе: {total_docs}\n"
        f"• Пользователей с сохраненными настройками: {active_users}\n"
        f"• Файлов в кэше изображений: {cache_files}"
    )

    await message.answer(stats_text)


@router.message(Command("reindex"))
async def cmd_reindex(message: Message) -> None:
    try:
        await message.answer("🔄 Начинаю переиндексацию базы знаний...")
        result = await rebuild_index()

        if result.get("success"):
            await message.answer(
                "✅ Переиндексация завершена.\n\n"
                f"📄 Обработано файлов: {result['documents_count']}\n"
                f"🧩 Создано чанков: {result['chunks_count']}"
            )
            return

        await message.answer(f"❌ Ошибка переиндексации: {result.get('error', 'неизвестная ошибка')}")
    except Exception:
        logger.exception("Failed to rebuild knowledge index.")
        await message.answer("❌ Произошла ошибка при переиндексации базы знаний.")
