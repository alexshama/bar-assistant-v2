"""
Shared utility helpers for services and handlers.
"""

from __future__ import annotations

import asyncio
import logging
import re
from html import escape
from typing import Awaitable, Callable, Optional, TypeVar

from config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "")


def prepare_tts_text(text: str, max_length: int = 500) -> str:
    clean_text = strip_html(text)
    clean_text = re.sub(r"[^\w\s\.,!?;:()-]", "", clean_text)
    clean_text = re.sub(r"\s+", " ", clean_text).strip()

    if len(clean_text) > max_length:
        clean_text = clean_text[:max_length].rstrip() + "..."

    return clean_text


def build_error_message(message: str) -> str:
    return f"😔 {escape(message)}"


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    attempts: Optional[int] = None,
    delay_seconds: Optional[float] = None,
    operation_name: str = "operation",
) -> T:
    max_attempts = attempts or settings.api_retry_attempts
    base_delay = delay_seconds if delay_seconds is not None else settings.api_retry_delay_seconds

    last_error: Optional[Exception] = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await operation()
        except Exception as error:  # pragma: no cover - defensive logging
            last_error = error
            if attempt >= max_attempts:
                break

            logger.warning(
                "Retrying %s after attempt %s/%s failed: %s",
                operation_name,
                attempt,
                max_attempts,
                error,
            )
            await asyncio.sleep(base_delay * attempt)

    assert last_error is not None
    raise last_error
