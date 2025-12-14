"""
OpenAI клиент для работы с API
"""

import logging
import asyncio
from typing import List, Optional, Dict, Any
from openai import AsyncOpenAI
from config import settings

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Клиент для работы с OpenAI API"""
    
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=60.0  # Увеличиваем таймаут до 60 секунд
        )
    
    async def chat(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> Optional[str]:
        """Отправка запроса к chat completion API"""
        try:
            model = model or settings.openai_chat_model
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Ошибка при обращении к OpenAI Chat API: {e}")
            return None
    
    async def embeddings(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Получение эмбеддингов для текстов"""
        try:
            response = await self.client.embeddings.create(
                model=settings.openai_embeddings_model,
                input=texts
            )
            
            return [item.embedding for item in response.data]
            
        except Exception as e:
            logger.error(f"Ошибка при получении эмбеддингов: {e}")
            return None
    
    async def stt(self, audio_path: str) -> Optional[str]:
        """Speech-to-Text транскрипция"""
        try:
            with open(audio_path, "rb") as audio_file:
                response = await self.client.audio.transcriptions.create(
                    model=settings.openai_stt_model,
                    file=audio_file,
                    language="ru"
                )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Ошибка при транскрипции аудио: {e}")
            return None
    
    async def tts(
        self, 
        text: str, 
        voice: str = "alloy",
        model: Optional[str] = None
    ) -> Optional[bytes]:
        """Text-to-Speech синтез"""
        try:
            model = model or settings.openai_tts_model
            
            response = await self.client.audio.speech.create(
                model=model,
                voice=voice,
                input=text
            )
            
            return response.content
            
        except Exception as e:
            logger.error(f"Ошибка при синтезе речи: {e}")
            return None
    
    async def vision(
        self, 
        image_bytes: bytes, 
        prompt: str,
        max_tokens: int = 500
    ) -> Optional[str]:
        """Анализ изображения через Vision API"""
        try:
            import base64
            
            # Кодируем изображение в base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Ошибка при анализе изображения: {e}")
            return None


# Глобальный экземпляр клиента
openai_client = OpenAIClient()