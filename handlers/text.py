"""
Обработчик текстовых сообщений
"""

import logging
from aiogram import Router, F
from aiogram.types import Message

from services.router import process_text_request
from services.tts import send_voice_response
from handlers.start import get_user_settings

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text)
async def handle_text_message(message: Message):
    """Обработка текстовых сообщений"""
    try:
        user_id = message.from_user.id
        user_text = message.text
        
        logger.info(f"Получен текстовый запрос от {user_id}: {user_text[:50]}...")
        
        # Отправляем индикатор "печатает"
        await message.bot.send_chat_action(message.chat.id, "typing")
        
        # Получаем настройки пользователя
        settings = get_user_settings(user_id)
        
        # Обрабатываем запрос через роутер
        response = await process_text_request(
            text=user_text,
            user_id=user_id,
            mode=settings["mode"]
        )
        
        # Отправляем текстовый ответ (рецепт)
        await message.answer(response["text"], parse_mode="HTML")
        
        # Если есть изображение для отправки - отправляем отдельным сообщением
        if response.get("image_bytes"):
            from aiogram.types import BufferedInputFile
            
            photo = BufferedInputFile(
                response["image_bytes"],
                filename="cocktail_image.png"
            )
            
            # Формируем подпись для изображения
            cocktail_name = "коктейля"
            if response.get("sources"):
                # Ищем источник, который использовался для генерации изображения
                # Это может быть не первый источник, а наиболее релевантный
                for source in response["sources"]:
                    chunk_id = source.get("chunk_id", "")
                    if "COCKTAIL" in chunk_id:
                        # Извлекаем название из ID чанка
                        parts = chunk_id.split("_")
                        if len(parts) >= 3:
                            name_part = "_".join(parts[2:])  # Берем все части после номера
                            cocktail_name = name_part.replace("_", " ").title()
                            
                            # Специальные случаи для красивых названий
                            name_replacements = {
                                "Long Island Iced Tea": "Long Island Iced Tea",
                                "B 52": "B-52",
                                "Old Fashioned": "Old Fashioned",
                                "Espresso Martini": "Espresso Martini"
                            }
                            
                            cocktail_name = name_replacements.get(cocktail_name, cocktail_name)
                            break
            
            caption = f"🖼 Изображение {cocktail_name}"
            
            await message.answer_photo(
                photo=photo,
                caption=caption
            )
        
        # Если включена озвучка и есть текст для озвучивания
        if settings["voice_enabled"] and response.get("tts_text"):
            await send_voice_response(
                message=message,
                text=response["tts_text"]
            )
            
    except Exception as e:
        logger.error(f"Ошибка при обработке текстового сообщения: {e}")
        await message.answer(
            "😔 Извините, произошла ошибка при обработке вашего запроса. "
            "Попробуйте еще раз или обратитесь к администратору."
        )