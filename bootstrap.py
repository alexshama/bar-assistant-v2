"""
Application bootstrap helpers.
"""

from __future__ import annotations

import logging

from config import settings
from rag.index import rebuild_index

logger = logging.getLogger(__name__)


async def initialize_application() -> None:
    settings.ensure_runtime_directories()

    if settings.auto_build_index_on_startup and not settings.simple_index_path.exists():
        logger.info("Knowledge base index not found. Building a fresh index on startup.")
        result = await rebuild_index()

        if not result.get("success"):
            logger.warning("Could not build knowledge index on startup: %s", result.get("error"))
