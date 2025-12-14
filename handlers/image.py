"""
Обработчик изображений
"""

import logging
import tempfile
from aiogram import Router, F
from aiogram.types import Message

from services.vision import analyze_image
from services.router import process_text_request
from handlers.start import get_user_settings

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.photo)
async def handle_photo_message(message: Message):
    """Обработка фотографий"""
    try:
        user_id = message.from_user.id
        
        logger.info(f"Получено изображение от {user_id}")
        
        # Отправляем индикатор "печатает"
        await message.bot.send_chat_action(message.chat.id, "typing")
        
        # Получаем самое большое фото
        photo = message.photo[-1]
        photo_file = await message.bot.get_file(photo.file_id)
        
        # Скачиваем изображение в память
        photo_bytes = await message.bot.download_file(photo_file.file_path)
        
        # Анализируем изображение через OpenAI Vision
        caption = message.caption or "Что изображено на этой фотографии? Это напиток или коктейль?"
        
        analysis_result = await analyze_image(
            image_bytes=photo_bytes.read(),
            prompt=f"Проанализируй это изображение как бармен-эксперт: {caption}"
        )
        
        if analysis_result:
            # Получаем настройки пользователя
            settings = get_user_settings(user_id)
            
            # Формируем ответ
            response_text = f"🔍 <b>Анализ изображения:</b>\n\n{analysis_result}"
            
            await message.answer(response_text, parse_mode="HTML")
            
            # Если пользователь хочет больше информации, обрабатываем через роутер
            if "коктейль" in analysis_result.lower() or "напиток" in analysis_result.lower():
                # Извлекаем название напитка для дополнительного поиска
                follow_up_query = f"Расскажи подробнее про {analysis_result[:100]}"
                
                follow_up_response = await process_text_request(
                    text=follow_up_query,
                    user_id=user_id,
                    mode=settings["mode"]
                )
                
                if follow_up_response.get("text"):
                    await message.answer(
                        f"📚 <b>Дополнительная информация:</b>\n\n{follow_up_response['text']}", 
                        parse_mode="HTML"
                    )
        else:
            await message.answer("😔 Не удалось проанализировать изображение. Попробуйте еще раз.")
            
    except Exception as e:
        logger.error(f"Ошибка при обработке изображения: {e}")
        await message.answer(
            "😔 Извините, произошла ошибка при анализе изображения. "
            "Попробуйте еще раз или обратитесь к администратору."
        )