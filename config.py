"""
Configuration and runtime settings for the application.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


BASE_DIR = Path(__file__).resolve().parent


def _read_env(name: str, default: Optional[str] = None, *, required: bool = False) -> str:
    value = os.getenv(name, default)

    if required and (value is None or not str(value).strip()):
        raise ValueError(
            "Missing required environment variables: "
            f"{name}. Copy `.env.example` to `.env` and fill in the missing values."
        )

    return "" if value is None else str(value).strip()


def _read_int(name: str, default: int) -> int:
    raw_value = _read_env(name, str(default))

    try:
        return int(raw_value)
    except ValueError as error:
        raise ValueError(f"Environment variable {name} must be an integer.") from error


def _read_float(name: str, default: float) -> float:
    raw_value = _read_env(name, str(default))

    try:
        return float(raw_value)
    except ValueError as error:
        raise ValueError(f"Environment variable {name} must be a float.") from error


def _read_bool(name: str, default: bool) -> bool:
    raw_value = _read_env(name, "1" if default else "0").lower()
    return raw_value in {"1", "true", "yes", "on"}


def _read_csv_ints(name: str) -> list[int]:
    raw_value = _read_env(name, "")
    values: list[int] = []

    if not raw_value:
        return values

    for chunk in raw_value.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            values.append(int(chunk))
        except ValueError as error:
            raise ValueError(f"Environment variable {name} must contain comma-separated integers.") from error

    return values


def _resolve_path(path_value: str) -> Path:
    candidate = Path(path_value)
    return candidate if candidate.is_absolute() else BASE_DIR / candidate


@dataclass
class Settings:
    telegram_bot_token: str = field(repr=False)
    openai_api_key: str = field(repr=False)
    openrouter_api_key: str = field(repr=False)

    openai_chat_model: str = "gpt-4o"
    openai_embeddings_model: str = "text-embedding-3-large"
    openai_tts_model: str = "tts-1"
    openai_stt_model: str = "whisper-1"
    openai_vision_model: str = "gpt-4o"

    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_image_model: str = "black-forest-labs/flux-1-schnell"
    openrouter_site_url: Optional[str] = None
    openrouter_app_name: str = "bartender-assistant"

    documents_path: Path = field(default_factory=lambda: BASE_DIR / "data" / "documents")
    chroma_db_path: Path = field(default_factory=lambda: BASE_DIR / "data" / "chroma_db")
    image_cache_path: Path = field(default_factory=lambda: BASE_DIR / "data" / "images")
    user_settings_path: Path = field(default_factory=lambda: BASE_DIR / "data" / "user_settings.json")

    rag_top_k: int = 5
    rag_score_threshold: float = 0.7

    request_timeout_seconds: int = 60
    api_retry_attempts: int = 2
    api_retry_delay_seconds: float = 1.0

    log_level: str = "INFO"
    auto_build_index_on_startup: bool = True
    admin_user_ids: list[int] = field(default_factory=list)

    system_prompt: str = (
        "Ты бармен-ассистент. Отвечай практично, коротко и по делу. "
        "Если это коктейль: дай рецепт в мл, метод, стекло, лед, гарнир, вкус. "
        "Если вопрос про выбор: предложи 2-3 варианта и почему. "
        "Если информации нет в базе, скажи честно и предложи ближайшее."
    )

    @property
    def simple_index_path(self) -> Path:
        return self.chroma_db_path / "simple_index.json"

    def ensure_runtime_directories(self) -> None:
        self.documents_path.mkdir(parents=True, exist_ok=True)
        self.chroma_db_path.mkdir(parents=True, exist_ok=True)
        self.image_cache_path.mkdir(parents=True, exist_ok=True)
        self.user_settings_path.parent.mkdir(parents=True, exist_ok=True)


def load_settings() -> Settings:
    missing = [
        name
        for name in ("TELEGRAM_BOT_TOKEN", "OPENAI_API_KEY", "OPENROUTER_API_KEY")
        if not _read_env(name, "").strip()
    ]

    if missing:
        raise ValueError(
            "Missing required environment variables: "
            f"{', '.join(missing)}. Copy `.env.example` to `.env` and provide valid values."
        )

    return Settings(
        telegram_bot_token=_read_env("TELEGRAM_BOT_TOKEN", required=True),
        openai_api_key=_read_env("OPENAI_API_KEY", required=True),
        openrouter_api_key=_read_env("OPENROUTER_API_KEY", required=True),
        openai_chat_model=_read_env("OPENAI_CHAT_MODEL", "gpt-4o"),
        openai_embeddings_model=_read_env("OPENAI_EMBEDDINGS_MODEL", "text-embedding-3-large"),
        openai_tts_model=_read_env("OPENAI_TTS_MODEL", "tts-1"),
        openai_stt_model=_read_env("OPENAI_STT_MODEL", "whisper-1"),
        openai_vision_model=_read_env("OPENAI_VISION_MODEL", "gpt-4o"),
        openrouter_base_url=_read_env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        openrouter_image_model=_read_env("OPENROUTER_IMAGE_MODEL", "black-forest-labs/flux-1-schnell"),
        openrouter_site_url=_read_env("OPENROUTER_SITE_URL", "") or None,
        openrouter_app_name=_read_env("OPENROUTER_APP_NAME", "bartender-assistant"),
        documents_path=_resolve_path(_read_env("DOCUMENTS_PATH", "data/documents")),
        chroma_db_path=_resolve_path(_read_env("CHROMA_DB_PATH", "data/chroma_db")),
        image_cache_path=_resolve_path(_read_env("IMAGE_CACHE_PATH", "data/images")),
        user_settings_path=_resolve_path(_read_env("USER_SETTINGS_PATH", "data/user_settings.json")),
        rag_top_k=_read_int("RAG_TOP_K", 5),
        rag_score_threshold=_read_float("RAG_SCORE_THRESHOLD", 0.7),
        request_timeout_seconds=_read_int("REQUEST_TIMEOUT_SECONDS", 60),
        api_retry_attempts=_read_int("API_RETRY_ATTEMPTS", 2),
        api_retry_delay_seconds=_read_float("API_RETRY_DELAY_SECONDS", 1.0),
        log_level=_read_env("LOG_LEVEL", "INFO").upper(),
        auto_build_index_on_startup=_read_bool("AUTO_BUILD_INDEX_ON_STARTUP", True),
        admin_user_ids=_read_csv_ints("ADMIN_USER_IDS"),
    )


settings = load_settings()
