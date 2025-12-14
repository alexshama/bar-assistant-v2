"""
Обработчик голосовых сообщений
"""

import logging
import os
import tempfile
from aiogram import Router, F
from aiogram.types import Message

from services.stt import transcribe_voice_message
from services.router import process_text_request
from services.tts import send_voice_response
from handlers.start import get_user_settings

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.voice)
async def handle_voice_message(message: Message):
    """Обработка голосовых сообщений"""
    try:
        user_id = message.from_user.id
        
        logger.info(f"Получено голосовое сообщение от {user_id}")
        
        # Отправляем индикатор "печатает"
        await message.bot.send_chat_action(message.chat.id, "typing")
        
        # Скачиваем голосовое сообщение
        voice_file = await message.bot.get_file(message.voice.file_id)
        
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
            temp_path = temp_file.name
            
        try:
            # Скачиваем файл
            await message.bot.download_file(voice_file.file_path, temp_path)
            
            # Транскрибируем голос в текст
            transcription = await transcribe_voice_message(temp_path)
            
            if not transcription:
                await message.answer(
                    "😔 Не удалось распознать речь.\n\n"
                    "Возможные причины:\n"
                    "• Временные проблемы с сетью\n"
                    "• Слишком тихая запись\n"
                    "• Плохое качество звука\n\n"
                    "Попробуйте еще раз или напишите текстом."
                )
                return
            
            logger.info(f"Транскрипция: {transcription}")
            
            # Отправляем распознанный текст пользователю
            await message.answer(f"🎤 Распознано: <i>{transcription}</i>", parse_mode="HTML")
            
            # Получаем настройки пользователя
            settings = get_user_settings(user_id)
            
            # Обрабатываем запрос через роутер
            response = await process_text_request(
                text=transcription,
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
            
            # Всегда отправляем голосовой ответ на голосовое сообщение
            if response.get("tts_text"):
                await send_voice_response(
                    message=message,
                    text=response["tts_text"]
                )
                
        finally:
            # Удаляем временный файл
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    except Exception as e:
        logger.error(f"Ошибка при обработке голосового сообщения: {e}")
        await message.answer(
            "😔 Извините, произошла ошибка при обработке голосового сообщения. "
            "Попробуйте еще раз или напишите текстом."
        )