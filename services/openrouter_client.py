"""
OpenRouter image generation client with fallback to OpenAI images.
"""

from __future__ import annotations

import base64
import logging
from typing import Optional

import aiohttp

from config import settings
from services.image_cache import image_cache

logger = logging.getLogger(__name__)


class OpenRouterClient:
    def __init__(self) -> None:
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url.rstrip("/")
        self.model = settings.openrouter_image_model
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        if settings.openrouter_site_url:
            self.headers["HTTP-Referer"] = settings.openrouter_site_url
        if settings.openrouter_app_name:
            self.headers["X-Title"] = settings.openrouter_app_name

    async def generate_image(self, prompt: str, cocktail_id: str | None = None) -> Optional[bytes]:
        try:
            if cocktail_id:
                cached = image_cache.get_cached_image(cocktail_id, prompt)
                if cached:
                    logger.info("Using cached image for %s", cocktail_id)
                    return cached

            result = await self._try_openrouter_image(prompt)
            if not result:
                logger.info("OpenRouter image generation failed, falling back to OpenAI images.")
                result = await self._try_openai_dalle(prompt)

            if result and cocktail_id:
                image_cache.save_to_cache(cocktail_id, prompt, result)

            return result
        except Exception as error:
            logger.error("Image generation failed: %s", error)
            return None

    async def _try_openrouter_image(self, prompt: str) -> Optional[bytes]:
        if "gemini" in self.model.lower():
            return await self._try_gemini_image(self._create_bar_prompt(prompt))

        payload = {
            "model": self.model,
            "prompt": self._create_bar_prompt(prompt),
            "negative_prompt": (
                "whipped cream, foam, toppings, garnish overload, decorations, herbs, "
                "multiple drinks, extra glasses, distorted layers"
            ),
            "n": 1,
            "size": "1024x1024",
        }

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=settings.request_timeout_seconds)) as session:
                async with session.post(
                    f"{self.base_url}/images/generations",
                    headers=self.headers,
                    json=payload,
                ) as response:
                    if response.status != 200:
                        logger.warning("OpenRouter image API returned status %s", response.status)
                        return None

                    result = await response.json()
                    image_url = result.get("data", [{}])[0].get("url")
                    return await self._download_image(image_url) if image_url else None
        except Exception as error:
            logger.warning("OpenRouter image API request failed: %s", error)
            return None

    async def _try_gemini_image(self, prompt: str) -> Optional[bytes]:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "modalities": ["image", "text"],
        }

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=settings.request_timeout_seconds)) as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                ) as response:
                    if response.status != 200:
                        logger.warning("Gemini image API returned status %s", response.status)
                        return None

                    result = await response.json()
                    message = result.get("choices", [{}])[0].get("message", {})
                    image_data = message.get("images", [{}])[0].get("image_url", {}).get("url")
                    if not image_data:
                        return None

                    if image_data.startswith("data:image"):
                        return base64.b64decode(image_data.split(",", 1)[1])

                    return await self._download_image(image_data)
        except Exception as error:
            logger.warning("Gemini image generation failed: %s", error)
            return None

    async def _try_openai_dalle(self, prompt: str) -> Optional[bytes]:
        try:
            from services.openai_client import openai_client

            refined_prompt = self._create_bar_prompt(prompt)
            response = await openai_client.client.images.generate(
                model="dall-e-3",
                prompt=refined_prompt[:1000],
                size="1024x1024",
                quality="standard",
                n=1,
            )
            image_url = response.data[0].url if response.data else None
            return await self._download_image(image_url) if image_url else None
        except Exception as error:
            logger.error("OpenAI image fallback failed: %s", error)
            return None

    def _create_bar_prompt(self, user_prompt: str) -> str:
        if "Professional cocktail photography" in user_prompt:
            return user_prompt

        return (
            "Generate a realistic cocktail image with professional bar presentation, "
            "appropriate glassware, clean garnish, elegant background, realistic lighting, "
            "single drink in frame, no text. User request: "
            f"{user_prompt}"
        )

    async def _download_image(self, image_url: str | None) -> Optional[bytes]:
        if not image_url:
            return None

        try:
            connector = aiohttp.TCPConnector(ssl=False)
            timeout = aiohttp.ClientTimeout(total=settings.request_timeout_seconds)
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        logger.error("Failed to download generated image: status %s", response.status)
                        return None
                    return await response.read()
        except Exception as error:
            logger.error("Failed to download generated image: %s", error)
            return None


openrouter_client = OpenRouterClient()
