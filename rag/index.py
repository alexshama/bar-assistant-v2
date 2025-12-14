"""
Индексация документов (упрощенная версия без ChromaDB)
"""

import os
import logging
import asyncio
import json
from typing import List, Dict, Any, Optional

from rag.loader import document_loader
from services.openai_client import openai_client
from config import settings

logger = logging.getLogger(__name__)


class DocumentIndexer:
    """Индексатор документов (упрощенная версия)"""
    
    def __init__(self):
        self.index_path = os.path.join(settings.chroma_db_path, "simple_index.json")
        self.documents_data = []
    
    def _init_storage(self):
        """Инициализация хранилища"""
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
    
    async def build_index(self) -> Dict[str, Any]:
        """Построение индекса из документов"""
        
        try:
            self._init_storage()
            
            # Загружаем документы
            logger.info("Загрузка документов...")
            documents = document_loader.load_documents()
            
            if not documents:
                return {
                    "success": False,
                    "error": "Не найдено документов для индексации",
                    "documents_count": 0,
                    "chunks_count": 0
                }
            
            # Сохраняем документы в простом формате
            logger.info("Сохранение документов в индекс...")
            self.documents_data = documents
            
            # Сохраняем в файл
            with open(self.index_path, 'w', encoding='utf-8') as f:
                json.dump(documents, f, ensure_ascii=False, indent=2)
            
            documents_count = len(set(doc['source_file'] for doc in documents))
            chunks_count = len(documents)
            
            logger.info(f"Индекс построен: {documents_count} файлов, {chunks_count} чанков")
            
            return {
                "success": True,
                "documents_count": documents_count,
                "chunks_count": chunks_count
            }
            
        except Exception as e:
            logger.error(f"Ошибка при построении индекса: {e}")
            return {
                "success": False,
                "error": str(e),
                "documents_count": 0,
                "chunks_count": 0
            }
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Получение информации о коллекции"""
        
        try:
            if os.path.exists(self.index_path):
                with open(self.index_path, 'r', encoding='utf-8') as f:
                    documents = json.load(f)
                
                return {
                    "success": True,
                    "collection_name": "simple_index",
                    "documents_count": len(documents),
                    "index_path": self.index_path
                }
            else:
                return {
                    "success": True,
                    "collection_name": "simple_index", 
                    "documents_count": 0,
                    "index_path": self.index_path
                }
            
        except Exception as e:
            logger.error(f"Ошибка при получении информации об индексе: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Глобальный экземпляр индексатора
document_indexer = DocumentIndexer()


async def rebuild_index() -> Dict[str, Any]:
    """Функция для перестроения индекса"""
    return await document_indexer.build_index()


async def get_index_info() -> Dict[str, Any]:
    """Функция для получения информации об индексе"""
    return document_indexer.get_collection_info()