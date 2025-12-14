"""
Speech-to-Text сервис
"""

import logging
import os
import tempfile
# from pydub import AudioSegment  # Временно отключено
from services.openai_client import openai_client

logger = logging.getLogger(__name__)


async def transcribe_voice_message(ogg_path: str) -> str:
    """Транскрипция голосового сообщения с fallback на разные сервисы"""
    
    wav_path = None
    
    try:
        # Конвертируем OGG в WAV для лучшей совместимости
        wav_path = await _convert_ogg_to_wav(ogg_path)
        
        if not wav_path:
            logger.error("Не удалось конвертировать аудио файл")
            return None
        
        # Сначала пробуем OpenRouter
        transcription = await _try_openrouter_stt(wav_path)
        
        if transcription:
            logger.info(f"Успешная транскрипция через OpenRouter: {transcription[:50]}...")
            return transcription.strip()
        
        # Fallback на OpenAI (если доступен)
        logger.info("OpenRouter недоступен, пробуем OpenAI...")
        transcription = await openai_client.stt(wav_path)
        
        if transcription:
            logger.info(f"Успешная транскрипция через OpenAI: {transcription[:50]}...")
            return transcription.strip()
        else:
            logger.error("Не удалось получить транскрипцию ни через один сервис")
            return None
            
    except Exception as e:
        logger.error(f"Ошибка при транскрипции: {e}")
        return None
        
    finally:
        # Удаляем временный WAV файл
        if wav_path and os.path.exists(wav_path):
            try:
                os.unlink(wav_path)
            except Exception as e:
                logger.warning(f"Не удалось удалить временный файл {wav_path}: {e}")


async def _try_openrouter_stt(audio_path: str) -> str:
    """Попытка транскрипции через OpenRouter"""
    try:
        import aiohttp
        from config import settings
        
        # Используем OpenRouter для STT
        url = "https://openrouter.ai/api/v1/audio/transcriptions"
        
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
        }
        
        # Читаем аудио файл
        with open(audio_path, 'rb') as audio_file:
            audio_data = audio_file.read()
        
        # Формируем multipart данные правильно
        data = aiohttp.FormData()
        data.add_field('file', audio_data, filename='audio.ogg', content_type='audio/ogg')
        data.add_field('model', 'openai/whisper-large-v3')
        data.add_field('language', 'ru')
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, 
                headers=headers, 
                data=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        return result.get('text', '').strip()
                    else:
                        error_text = await response.text()
                        logger.warning(f"OpenRouter STT недоступен: {response.status} - {error_text}")
                        return None
                        
    except Exception as e:
        logger.warning(f"Ошибка OpenRouter STT: {e}")
        return None


async def _convert_ogg_to_wav(ogg_path: str) -> str:
    """Конвертация OGG в WAV (упрощенная версия)"""
    
    try:
        # Временно возвращаем исходный файл без конвертации
        # OpenAI Whisper поддерживает OGG напрямую
        logger.info(f"Используем OGG файл напрямую: {ogg_path}")
        return ogg_path
        
    except Exception as e:
        logger.error(f"Ошибка при обработке аудио: {e}")
        return None