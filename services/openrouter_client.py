"""
OpenRouter клиент для генерации изображений
"""

import logging
import aiohttp
import asyncio
from typing import Optional
from config import settings
from services.image_cache import image_cache

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Клиент для работы с OpenRouter API"""
    
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.model = settings.openrouter_image_model
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Добавляем дополнительные заголовки если указаны
        if settings.openrouter_site_url:
            self.headers["HTTP-Referer"] = settings.openrouter_site_url
        if settings.openrouter_app_name:
            self.headers["X-Title"] = settings.openrouter_app_name
    
    async def generate_image(self, prompt: str, cocktail_id: str = None) -> Optional[bytes]:
        """Генерация изображения через OpenRouter с кэшированием"""
        try:
            # Сначала проверяем кэш (если есть ID коктейля)
            if cocktail_id:
                cached_image = image_cache.get_cached_image(cocktail_id, prompt)
                if cached_image:
                    logger.info(f"Используем кэшированное изображение для {cocktail_id}")
                    return cached_image
            
            # Если в кэше нет, генерируем новое
            logger.info(f"Генерируем новое изображение для {cocktail_id or 'unknown'}")
            
            # Пробуем OpenRouter (Gemini)
            result = await self._try_openrouter_image(prompt)
            if not result:
                # Если OpenRouter не работает, используем OpenAI DALL-E
                logger.info("OpenRouter недоступен, используем OpenAI DALL-E как fallback")
                result = await self._try_openai_dalle(prompt)
            
            # Сохраняем в кэш (если есть ID коктейля и изображение сгенерировано)
            if result and cocktail_id:
                image_cache.save_to_cache(cocktail_id, prompt, result)
                logger.info(f"Изображение сохранено в кэш для {cocktail_id}")
            
            return result
                        
        except Exception as e:
            logger.error(f"Ошибка при генерации изображения: {e}")
            return None
    
    async def _try_openrouter_image(self, prompt: str) -> Optional[bytes]:
        """Попытка генерации через OpenRouter"""
        try:
            # Формируем барный промпт
            bar_prompt = self._create_bar_prompt(prompt)
            
            logger.info(f"Пробуем OpenRouter с моделью {self.model}")
            
            # Проверяем, это Gemini модель или нет
            if "gemini" in self.model.lower():
                return await self._try_gemini_image(bar_prompt)
            
            # Для других моделей (Flux и т.д.) используем старый метод
            data = {
                "model": self.model,
                "prompt": bar_prompt,
                "negative_prompt": "whipped cream, foam, toppings, garnish, decorations, herbs, leaves, rosemary, mint, cream on top, foam on top, green layer, 4 layers, 5 layers, multiple layers, extra layers",
                "n": 1,
                "size": "1024x1024"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/images/generations",
                    headers=self.headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        if "data" in result and len(result["data"]) > 0:
                            image_url = result["data"][0].get("url")
                            if image_url:
                                return await self._download_image(image_url)
                    else:
                        error_text = await response.text()
                        logger.warning(f"OpenRouter недоступен: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.warning(f"OpenRouter не работает: {e}")
            return None
    
    async def _try_gemini_image(self, prompt: str) -> Optional[bytes]:
        """Генерация изображения через Gemini"""
        try:
            logger.info("Используем Gemini для генерации изображения")
            
            # Для Gemini используем chat/completions endpoint с modalities
            data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "modalities": ["image", "text"]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        # Ищем изображение в ответе
                        if "choices" in result and len(result["choices"]) > 0:
                            choice = result["choices"][0]
                            message = choice.get("message", {})
                            
                            # Проверяем images в message
                            if "images" in message and len(message["images"]) > 0:
                                image_data = message["images"][0].get("image_url", {}).get("url")
                                if image_data:
                                    logger.info(f"Получено изображение от Gemini")
                                    
                                    # Проверяем, это Base64 или URL
                                    if image_data.startswith("data:image"):
                                        # Base64 data URL
                                        import base64
                                        # Извлекаем base64 данные после "data:image/png;base64,"
                                        base64_data = image_data.split(",", 1)[1]
                                        return base64.b64decode(base64_data)
                                    else:
                                        # Обычный URL
                                        return await self._download_image(image_data)
                    else:
                        error_text = await response.text()
                        logger.warning(f"Gemini вернул ошибку: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.warning(f"Ошибка при генерации через Gemini: {e}")
            return None
    
    async def _try_openai_dalle(self, prompt: str) -> Optional[bytes]:
        """Fallback на OpenAI DALL-E"""
        try:
            from services.openai_client import openai_client
            
            bar_prompt = self._create_bar_prompt(prompt)
            
            # Для DALL-E создаем более строгий промпт без негативных слов
            dalle_prompt = bar_prompt.replace("cream liqueur", "Irish liqueur").replace("cream", "liqueur")
            dalle_prompt += " Simple clean shot glass with three liquid layers only."
            
            # Используем OpenAI для генерации изображения
            response = await openai_client.client.images.generate(
                model="dall-e-3",
                prompt=dalle_prompt[:1000],  # DALL-E имеет ограничение на длину промпта
                size="1024x1024",
                quality="standard",
                n=1
            )
            
            if response.data:
                image_url = response.data[0].url
                return await self._download_image(image_url)
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка OpenAI DALL-E: {e}")
            return None
    
    def _create_bar_prompt(self, user_prompt: str) -> str:
        """Создание барного промпта для изображения"""
        
        # Если промпт уже детальный и профессиональный, используем его как есть
        if "Professional cocktail photography" in user_prompt:
            return user_prompt
        
        # Для общих промптов добавляем базовую информацию
        base_prompt = """Generate a high-quality, realistic image of a cocktail or drink. 
        The image should show:
        - Professional bar presentation
        - Appropriate glassware
        - Proper garnish and decoration
        - Bar counter or elegant background
        - Good lighting and composition
        - No text or writing on the image
        
        User request: """
        
        return base_prompt + user_prompt
    
    def _extract_image_url(self, content: str) -> Optional[str]:
        """Извлечение URL изображения из ответа"""
        # Здесь нужно будет адаптировать под конкретный формат ответа Gemini Image
        # Пока используем простой поиск URL
        import re
        
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, content)
        
        for url in urls:
            if any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                return url
        
        return None
    
    async def _download_image(self, image_url: str) -> Optional[bytes]:
        """Скачивание изображения по URL"""
        try:
            # Настройки для обхода SSL проблем
            connector = aiohttp.TCPConnector(ssl=False)
            timeout = aiohttp.ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        logger.error(f"Ошибка при скачивании изображения: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Ошибка при скачивании изображения: {e}")
            # Попробуем альтернативный способ через requests
            try:
                import requests
                response = requests.get(image_url, timeout=30, verify=False)
                if response.status_code == 200:
                    return response.content
                else:
                    logger.error(f"Requests также не смог скачать: {response.status_code}")
                    return None
            except Exception as e2:
                logger.error(f"И requests не помог: {e2}")
                return None


# Глобальный экземпляр клиента
openrouter_client = OpenRouterClient()