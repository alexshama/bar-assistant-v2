"""
Конфигурация приложения
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()


@dataclass
class Settings:
    """Настройки приложения"""
    
    # Обязательные поля (без значений по умолчанию)
    telegram_bot_token: str
    openai_api_key: str
    openrouter_api_key: str
    
    # Поля с значениями по умолчанию
    openai_chat_model: str = "gpt-4o"
    openai_embeddings_model: str = "text-embedding-3-large"
    openai_tts_model: str = "tts-1"
    openai_stt_model: str = "whisper-1"
    
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_image_model: str = "black-forest-labs/flux-1-schnell"
    openrouter_site_url: Optional[str] = None
    openrouter_app_name: str = "bartender-assistant"
    
    chroma_db_path: str = "data/chroma_db"
    documents_path: str = "data/documents"
    rag_top_k: int = 5
    rag_score_threshold: float = 0.7
    
    system_prompt: str = """Ты бармен-ассистент. Отвечай практично, коротко и по делу. 
    Если это коктейль: дай рецепт в мл, метод, стекло, лёд, гарнир, вкус. 
    Если вопрос про выбор: предложи 2–3 варианта и почему. 
    Если информации нет в базе — скажи честно и предложи ближайшее."""


def load_settings() -> Settings:
    """Загрузка настроек из переменных окружения"""
    
    # Проверяем обязательные переменные
    required_vars = [
        "TELEGRAM_BOT_TOKEN",
        "OPENAI_API_KEY", 
        "OPENROUTER_API_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}")
    
    return Settings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_chat_model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o"),
        openai_embeddings_model=os.getenv("OPENAI_EMBEDDINGS_MODEL", "text-embedding-3-large"),
        openai_tts_model=os.getenv("OPENAI_TTS_MODEL", "tts-1"),
        openai_stt_model=os.getenv("OPENAI_STT_MODEL", "whisper-1"),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
        openrouter_base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        openrouter_image_model=os.getenv("OPENROUTER_IMAGE_MODEL", "black-forest-labs/flux-1-schnell"),
        openrouter_site_url=os.getenv("OPENROUTER_SITE_URL"),
        openrouter_app_name=os.getenv("OPENROUTER_APP_NAME", "bartender-assistant"),
        chroma_db_path=os.getenv("CHROMA_DB_PATH", "data/chroma_db"),
        documents_path=os.getenv("DOCUMENTS_PATH", "data/documents"),
        rag_top_k=int(os.getenv("RAG_TOP_K", "5")),
        rag_score_threshold=float(os.getenv("RAG_SCORE_THRESHOLD", "0.7"))
    )


# Глобальный экземпляр настроек
settings = load_settings()