"""
Image cache service.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)


class ImageCache:
    CACHE_VERSION = "v2"

    def __init__(self, cache_dir: Path | str | None = None) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir else settings.image_cache_path
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Initialized image cache in %s", self.cache_dir)

    def _get_cache_key(self, cocktail_id: str, prompt: str) -> str:
        normalized_id = cocktail_id.upper().replace("COCKTAIL_", "").replace("_", "-")
        normalized_prompt = " ".join(prompt.lower().split())
        prompt_hash = hashlib.md5(
            f"{self.CACHE_VERSION}:{normalized_id}:{normalized_prompt}".encode("utf-8")
        ).hexdigest()[:12]
        return f"{cocktail_id}_{prompt_hash}"

    def _find_cache_file(self, cache_key: str) -> Optional[Path]:
        for suffix in (".png", ".jpg", ".jpeg"):
            candidate = self.cache_dir / f"{cache_key}{suffix}"
            if candidate.exists():
                return candidate
        return None

    def get_cached_image(self, cocktail_id: str, prompt: str) -> Optional[bytes]:
        try:
            cache_key = self._get_cache_key(cocktail_id, prompt)
            cache_path = self._find_cache_file(cache_key)
            if not cache_path:
                return None

            return cache_path.read_bytes()
        except Exception as error:
            logger.error("Failed to read image cache: %s", error)
            return None

    def save_to_cache(self, cocktail_id: str, prompt: str, image_bytes: bytes) -> bool:
        try:
            cache_key = self._get_cache_key(cocktail_id, prompt)
            cache_path = self.cache_dir / f"{cache_key}.png"
            cache_path.write_bytes(image_bytes)
            return True
        except Exception as error:
            logger.error("Failed to save image cache: %s", error)
            return False

    def clear_cache(self) -> int:
        removed = 0
        for cache_file in self.cache_dir.glob("*.*"):
            if cache_file.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
                continue
            cache_file.unlink(missing_ok=True)
            removed += 1
        return removed

    def get_cache_stats(self) -> dict:
        try:
            cache_files = [
                path for path in self.cache_dir.glob("*.*") if path.suffix.lower() in {".png", ".jpg", ".jpeg"}
            ]
            total_size = sum(path.stat().st_size for path in cache_files)
            return {
                "total_files": len(cache_files),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "cache_dir": str(self.cache_dir),
            }
        except Exception as error:
            logger.error("Failed to collect cache stats: %s", error)
            return {"error": str(error)}


image_cache = ImageCache()
