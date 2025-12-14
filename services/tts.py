"""
Text-to-Speech сервис
"""

import logging
import tempfile
import os
from aiogram.types import Message, FSInputFile
from services.openai_client import openai_client

logger = logging.getLogger(__name__)


async def send_voice_response(message: Message, text: str, voice: str = "alloy") -> bool:
    """Отправка голосового ответа пользователю"""
    
    temp_path = None
    
    try:
        # Генерируем аудио через OpenAI TTS
        audio_bytes = await openai_client.tts(text, voice)
        
        if not audio_bytes:
            logger.error("Не удалось сгенерировать аудио")
            return False
        
        # Сохраняем во временный файл
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(audio_bytes)
        
        # Отправляем голосовое сообщение
        audio_file = FSInputFile(temp_path)
        await message.answer_voice(audio_file)
        
        logger.info(f"Голосовой ответ отправлен пользователю {message.from_user.id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при отправке голосового ответа: {e}")
        return False
        
    finally:
        # Удаляем временный файл
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Не удалось удалить временный файл {temp_path}: {e}")


async def synthesize_speech(text: str, voice: str = "alloy") -> bytes:
    """Синтез речи без отправки (для других целей)"""
    
    try:
        audio_bytes = await openai_client.tts(text, voice)
        return audio_bytes
        
    except Exception as e:
        logger.error(f"Ошибка при синтезе речи: {e}")
        return None