"""
Сервис анализа изображений через OpenAI Vision
"""

import logging
from typing import Optional
from services.openai_client import openai_client

logger = logging.getLogger(__name__)


async def analyze_image(image_bytes: bytes, prompt: str) -> Optional[str]:
    """Анализ изображения через OpenAI Vision API"""
    
    try:
        # Формируем промпт для анализа как бармен-эксперт
        bar_prompt = f"""
        Ты опытный бармен и эксперт по напиткам. Проанализируй это изображение и ответь на русском языке.
        
        {prompt}
        
        Если это коктейль или напиток:
        - Определи название напитка
        - Опиши внешний вид и подачу
        - Укажи тип стекла/бокала
        - Отметь гарниры и декор
        - Оцени качество подачи
        
        Если это не напиток, кратко опиши что изображено.
        """
        
        result = await openai_client.vision(image_bytes, bar_prompt)
        
        if result:
            logger.info(f"Изображение проанализировано: {result[:100]}...")
            return result
        else:
            logger.error("Не удалось проанализировать изображение")
            return None
            
    except Exception as e:
        logger.error(f"Ошибка при анализе изображения: {e}")
        return None


async def identify_drink(image_bytes: bytes) -> Optional[str]:
    """Специализированная функция для идентификации напитков"""
    
    prompt = """
    Определи что за напиток изображен на фото. 
    Назови его точное название если можешь определить, 
    или опиши тип напитка (коктейль, пиво, вино и т.д.).
    """
    
    return await analyze_image(image_bytes, prompt)


async def analyze_bar_setup(image_bytes: bytes) -> Optional[str]:
    """Анализ барной стойки или сетапа"""
    
    prompt = """
    Проанализируй барную стойку или рабочее место бармена на изображении.
    Опиши оборудование, инструменты, ингредиенты которые видишь.
    Дай советы по улучшению организации рабочего места если нужно.
    """
    
    return await analyze_image(image_bytes, prompt)