"""
Vision helpers built on top of OpenAI.
"""

from __future__ import annotations

import logging
from typing import Optional

from services.openai_client import openai_client

logger = logging.getLogger(__name__)


async def analyze_image(image_bytes: bytes, prompt: str) -> Optional[str]:
    try:
        bar_prompt = (
            "Ты опытный бармен и эксперт по напиткам. Проанализируй изображение и ответь на русском языке. "
            "Если это напиток, назови его, опиши подачу, стекло, гарнир и качество сервировки. "
            "Если это не напиток, кратко опиши содержимое изображения. "
            f"{prompt}"
        )
        return await openai_client.vision(image_bytes, bar_prompt)
    except Exception as error:
        logger.error("Image analysis failed: %s", error)
        return None


async def identify_drink(image_bytes: bytes) -> Optional[str]:
    return await analyze_image(
        image_bytes,
        "Определи, какой напиток изображен на фото. Дай точное название, если уверен.",
    )


async def analyze_bar_setup(image_bytes: bytes) -> Optional[str]:
    return await analyze_image(
        image_bytes,
        "Проанализируй барную станцию и дай советы по организации рабочего места.",
    )
