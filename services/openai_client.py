"""
OpenAI client wrapper used by the bot.
"""

from __future__ import annotations

import base64
import logging
from typing import Any, Optional

from openai import AsyncOpenAI

from config import settings
from services.utils import retry_async

logger = logging.getLogger(__name__)


class OpenAIClient:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=float(settings.request_timeout_seconds),
        )

    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> Optional[str]:
        async def operation() -> Any:
            return await self.client.chat.completions.create(
                model=model or settings.openai_chat_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

        try:
            response = await retry_async(operation, operation_name="OpenAI chat")
            content = response.choices[0].message.content if response.choices else None
            return content.strip() if content else None
        except Exception as error:
            logger.error("OpenAI chat request failed: %s", error)
            return None

    async def embeddings(self, texts: list[str]) -> Optional[list[list[float]]]:
        async def operation() -> Any:
            return await self.client.embeddings.create(
                model=settings.openai_embeddings_model,
                input=texts,
            )

        try:
            response = await retry_async(operation, operation_name="OpenAI embeddings")
            return [item.embedding for item in response.data]
        except Exception as error:
            logger.error("OpenAI embeddings request failed: %s", error)
            return None

    async def stt(self, audio_path: str) -> Optional[str]:
        try:
            with open(audio_path, "rb") as audio_file:
                response = await self.client.audio.transcriptions.create(
                    model=settings.openai_stt_model,
                    file=audio_file,
                    language="ru",
                )
            return response.text.strip() if response.text else None
        except Exception as error:
            logger.error("OpenAI STT request failed: %s", error)
            return None

    async def tts(
        self,
        text: str,
        voice: str = "alloy",
        model: Optional[str] = None,
    ) -> Optional[bytes]:
        async def operation() -> Any:
            return await self.client.audio.speech.create(
                model=model or settings.openai_tts_model,
                voice=voice,
                input=text,
            )

        try:
            response = await retry_async(operation, operation_name="OpenAI TTS")
            return response.content
        except Exception as error:
            logger.error("OpenAI TTS request failed: %s", error)
            return None

    async def vision(
        self,
        image_bytes: bytes,
        prompt: str,
        max_tokens: int = 500,
    ) -> Optional[str]:
        encoded_image = base64.b64encode(image_bytes).decode("utf-8")

        async def operation() -> Any:
            return await self.client.chat.completions.create(
                model=settings.openai_vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"},
                            },
                        ],
                    }
                ],
                max_tokens=max_tokens,
            )

        try:
            response = await retry_async(operation, operation_name="OpenAI vision")
            content = response.choices[0].message.content if response.choices else None
            return content.strip() if content else None
        except Exception as error:
            logger.error("OpenAI vision request failed: %s", error)
            return None


openai_client = OpenAIClient()
