"""
Lightweight JSON index builder for RAG documents.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from config import settings
from rag.loader import document_loader

logger = logging.getLogger(__name__)


class DocumentIndexer:
    def __init__(self) -> None:
        self.index_path: Path = settings.simple_index_path

    async def build_index(self) -> dict[str, Any]:
        try:
            self.index_path = settings.simple_index_path
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            documents = document_loader.__class__(settings.documents_path).load_documents()

            if not documents:
                return {
                    "success": False,
                    "error": "Не найдено документов для индексации.",
                    "documents_count": 0,
                    "chunks_count": 0,
                }

            with self.index_path.open("w", encoding="utf-8") as file:
                json.dump(documents, file, ensure_ascii=False, indent=2)

            source_files = {document["source_file"] for document in documents}
            return {
                "success": True,
                "documents_count": len(source_files),
                "chunks_count": len(documents),
            }
        except Exception as error:
            logger.error("Failed to build knowledge index: %s", error)
            return {
                "success": False,
                "error": str(error),
                "documents_count": 0,
                "chunks_count": 0,
            }

    def get_collection_info(self) -> dict[str, Any]:
        try:
            self.index_path = settings.simple_index_path
            if not self.index_path.exists():
                return {
                    "success": True,
                    "collection_name": "simple_index",
                    "documents_count": 0,
                    "index_path": str(self.index_path),
                }

            with self.index_path.open("r", encoding="utf-8") as file:
                documents = json.load(file)

            return {
                "success": True,
                "collection_name": "simple_index",
                "documents_count": len(documents),
                "index_path": str(self.index_path),
            }
        except Exception as error:
            logger.error("Failed to inspect knowledge index: %s", error)
            return {"success": False, "error": str(error)}


document_indexer = DocumentIndexer()


async def rebuild_index() -> dict[str, Any]:
    return await document_indexer.build_index()


async def get_index_info() -> dict[str, Any]:
    return document_indexer.get_collection_info()
