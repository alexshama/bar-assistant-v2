"""
Document loader for the lightweight RAG layer.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from config import settings

logger = logging.getLogger(__name__)


class DocumentLoader:
    def __init__(self, documents_path: str | Path | None = None) -> None:
        self.documents_path = Path(documents_path) if documents_path else settings.documents_path

    def load_documents(self) -> list[dict[str, Any]]:
        documents: list[dict[str, Any]] = []
        if not self.documents_path.exists():
            logger.warning("Documents directory not found: %s", self.documents_path)
            return documents

        for file_path in sorted(self.documents_path.glob("*.txt")):
            try:
                documents.extend(self._load_file(file_path))
            except Exception as error:
                logger.error("Failed to load %s: %s", file_path.name, error)

        logger.info("Loaded %s document chunks.", len(documents))
        return documents

    def _load_file(self, file_path: Path) -> list[dict[str, Any]]:
        content = file_path.read_text(encoding="utf-8")
        if "[CHUNK]" in content:
            return self._parse_chunked_format(content, file_path.name)
        return self._parse_plain_text(content, file_path.name)

    def _parse_chunked_format(self, content: str, filename: str) -> list[dict[str, Any]]:
        documents: list[dict[str, Any]] = []
        chunks = content.split("[CHUNK]")[1:]

        for index, chunk in enumerate(chunks):
            document = self._parse_chunk(chunk.strip(), filename, index)
            if document:
                documents.append(document)

        return documents

    def _parse_chunk(self, chunk_text: str, filename: str, chunk_index: int) -> dict[str, Any] | None:
        chunk_data: dict[str, Any] = {
            "chunk_id": f"{filename}_{chunk_index}",
            "tags": [],
            "keywords": [],
            "text": "",
            "source_file": filename,
        }
        text_lines: list[str] = []

        for line in chunk_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("id:"):
                chunk_data["chunk_id"] = stripped[3:].strip()
            elif stripped.startswith("tags:"):
                chunk_data["tags"] = [item.strip() for item in stripped[5:].split(",") if item.strip()]
            elif stripped.startswith("keywords:"):
                chunk_data["keywords"] = [item.strip() for item in stripped[9:].split(",") if item.strip()]
            elif stripped.startswith("text:"):
                text_lines.append(stripped[5:].strip())
            else:
                text_lines.append(stripped)

        chunk_data["text"] = "\n".join(text_lines).strip()
        return chunk_data if chunk_data["text"] else None

    def _parse_plain_text(self, content: str, filename: str) -> list[dict[str, Any]]:
        documents: list[dict[str, Any]] = []
        paragraphs = [paragraph.strip() for paragraph in content.split("\n\n") if paragraph.strip()]

        for index, paragraph in enumerate(paragraphs):
            if len(paragraph) < 50:
                continue
            documents.append(
                {
                    "chunk_id": f"{filename}_paragraph_{index}",
                    "tags": [self._extract_category_from_filename(filename)],
                    "keywords": self._extract_keywords_from_text(paragraph),
                    "text": paragraph,
                    "source_file": filename,
                }
            )

        return documents

    def _extract_category_from_filename(self, filename: str) -> str:
        filename_lower = filename.lower()
        if "cocktail" in filename_lower or "коктейль" in filename_lower:
            return "коктейли"
        if "beer" in filename_lower or "пиво" in filename_lower:
            return "пиво"
        if "whisky" in filename_lower or "whiskey" in filename_lower or "виски" in filename_lower:
            return "виски"
        if "vodka" in filename_lower or "водка" in filename_lower:
            return "водка"
        if "gin" in filename_lower or "джин" in filename_lower:
            return "джин"
        if "rum" in filename_lower or "ром" in filename_lower:
            return "ром"
        if "wine" in filename_lower or "вино" in filename_lower:
            return "вино"
        return "общее"

    def _extract_keywords_from_text(self, text: str) -> list[str]:
        bar_keywords = [
            "коктейль",
            "напиток",
            "алкоголь",
            "пиво",
            "виски",
            "водка",
            "джин",
            "ром",
            "текила",
            "вино",
            "шампанское",
            "ликер",
            "сироп",
            "биттер",
            "лед",
            "гарнир",
            "бокал",
            "стакан",
            "шейкер",
            "стрейнер",
            "бар",
            "бармен",
            "рецепт",
            "мл",
            "унция",
            "dash",
            "splash",
            "мудлинг",
            "стир",
            "шейк",
            "билд",
        ]
        text_lower = text.lower()
        return [keyword for keyword in bar_keywords if keyword in text_lower][:10]


document_loader = DocumentLoader()
