"""
Query layer for the lightweight knowledge base.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

from config import settings

logger = logging.getLogger(__name__)


class KnowledgeBaseQuery:
    def __init__(self) -> None:
        self.index_path: Path = settings.simple_index_path
        self.documents: list[dict[str, Any]] = []

    def _load_documents(self) -> None:
        try:
            self.index_path = settings.simple_index_path
            if not self.index_path.exists():
                self.documents = []
                return

            with self.index_path.open("r", encoding="utf-8") as file:
                self.documents = json.load(file)
        except Exception as error:
            logger.error("Failed to load knowledge index: %s", error)
            self.documents = []

    async def search(
        self,
        query: str,
        top_k: int | None = None,
        score_threshold: float | None = None,
    ) -> Optional[dict[str, Any]]:
        top_k = top_k or settings.rag_top_k
        threshold = score_threshold if score_threshold is not None else 0.0

        self._load_documents()
        if not self.documents:
            return {"documents": [], "sources": [], "query": query}

        normalized_query = self._normalize_query(query)
        scored_results: list[dict[str, Any]] = []

        for document in self.documents:
            score = self._calculate_text_score(normalized_query, document)
            if score <= threshold:
                continue
            scored_results.append(
                {
                    "document": document["text"],
                    "metadata": document,
                    "score": score,
                }
            )

        scored_results.sort(key=lambda item: item["score"], reverse=True)
        scored_results = scored_results[:top_k]

        return {
            "documents": [self._build_response_document(item["document"], item["metadata"]) for item in scored_results],
            "sources": [
                {
                    "chunk_id": item["metadata"].get("chunk_id", "unknown"),
                    "source_file": item["metadata"].get("source_file", "unknown"),
                    "tags": item["metadata"].get("tags", []),
                    "keywords": item["metadata"].get("keywords", []),
                    "score": item["score"],
                    "distance": max(0.0, 1 - item["score"]),
                }
                for item in scored_results
            ],
            "query": query,
        }

    def _build_response_document(self, document_text: str, metadata: dict[str, Any]) -> str:
        chunk_id = metadata.get("chunk_id", "")
        humanized_title = chunk_id.replace("_", " ").strip()
        translations = {
            "negroni": "негрони",
            "martini": "мартини",
            "mojito": "мохито",
            "margarita": "маргарита",
            "daiquiri": "дайкири",
            "cosmopolitan": "космополитен",
            "manhattan": "манхэттен",
            "whisky": "виски",
            "vodka": "водка",
            "gin": "джин",
            "rum": "ром",
            "lager": "лагер",
            "ale": "эль",
        }
        for english, russian in translations.items():
            humanized_title = re.sub(rf"\b{english}\b", russian, humanized_title, flags=re.IGNORECASE)
        if not humanized_title:
            return document_text

        first_token = humanized_title.split()[0].lower()
        if first_token and first_token in document_text.lower():
            return document_text

        return f"{humanized_title}. {document_text}"

    def _calculate_text_score(self, query: str, document: dict[str, Any]) -> float:
        score = 0.0
        text_lower = document["text"].lower()
        chunk_id_lower = document.get("chunk_id", "").lower()
        query_words = query.split()

        exact_matches = {
            "b 52": "b-52",
            "негрони": "negroni",
            "мартини": "martini",
            "мохито": "mojito",
            "маргарита": "margarita",
            "годфазер": "godfather",
            "манхэттен": "manhattan",
            "космополитен": "cosmopolitan",
            "дайкири": "daiquiri",
            "сингапур слинг": "singapore_sling",
            "виски": "whisky",
            "whisky": "whisky",
            "whiskey": "whisky",
            "водка": "vodka",
            "джин": "gin",
            "ром": "rum",
            "коньяк": "cognac",
            "бренди": "brandy",
            "пилснер": "pilsner",
            "лагер": "lager",
            "эль": "ale",
        }

        for query_name, standard_name in exact_matches.items():
            if query_name in query:
                if standard_name in chunk_id_lower:
                    score += 10.0
                if standard_name in text_lower:
                    score += 3.0
                for keyword in document.get("keywords", []):
                    if standard_name in keyword.lower() or query_name in keyword.lower():
                        score += 5.0

        for word in query_words:
            if len(word) < 2:
                continue
            if word in chunk_id_lower:
                score += 3.0
            if word in text_lower:
                score += 1.0
            for keyword in document.get("keywords", []):
                if word in keyword.lower():
                    score += 2.0
            for tag in document.get("tags", []):
                if word in tag.lower():
                    score += 1.5

        if any(phrase in query for phrase in ("что такое", "что это", "определение")):
            if "_def_" in chunk_id_lower:
                score += 15.0
            if any(tag in {"basics", "definition"} for tag in document.get("tags", [])):
                score += 10.0
            if "cocktail" in document.get("tags", []):
                score -= 5.0
        elif "cocktail" in document.get("tags", []) and any(
            word in query for word in ("коктейль", "рецепт", "покажи", "сделать")
        ):
            score += 1.0

        return score

    def _normalize_query(self, query: str) -> str:
        query_lower = re.sub(r"[^\w\s-]", "", query.lower().strip()).replace("-", " ")
        replacements = {
            "маргариты": "маргарита",
            "манхэттена": "манхэттен",
            "космополитена": "космополитен",
            "годфазера": "годфазер",
            "б52": "b 52",
            "б 52": "b 52",
        }
        for source, target in replacements.items():
            query_lower = query_lower.replace(source, target)

        stop_words = {
            "как",
            "сделать",
            "приготовить",
            "что",
            "такое",
            "это",
            "покажи",
            "фото",
            "изображение",
            "мне",
            "рецепт",
        }

        if any(phrase in query_lower for phrase in ("как сделать", "как приготовить", "покажи", "рецепт")):
            filtered = [word for word in query_lower.split() if word not in stop_words and len(word) > 1]
            if filtered:
                return " ".join(filtered)

        return query_lower

    async def search_by_tags(self, tags: list[str], top_k: int | None = None) -> Optional[dict[str, Any]]:
        top_k = top_k or settings.rag_top_k
        self._load_documents()

        matching = []
        for document in self.documents:
            doc_tags = [tag.lower() for tag in document.get("tags", [])]
            if any(tag.lower() in doc_tags for tag in tags):
                matching.append(
                    {
                        "document": document["text"],
                        "metadata": document,
                        "score": 1.0,
                    }
                )

        matching = matching[:top_k]
        return {
            "documents": [item["document"] for item in matching],
            "sources": [
                {
                    "chunk_id": item["metadata"].get("chunk_id", "unknown"),
                    "source_file": item["metadata"].get("source_file", "unknown"),
                    "tags": item["metadata"].get("tags", []),
                    "keywords": item["metadata"].get("keywords", []),
                    "score": item["score"],
                    "distance": 0.0,
                }
                for item in matching
            ],
            "query": f"tags: {', '.join(tags)}",
        }

    def get_stats(self) -> dict[str, Any]:
        self._load_documents()
        source_files = sorted({document.get("source_file", "") for document in self.documents if document.get("source_file")})
        tags = sorted({tag for document in self.documents for tag in document.get("tags", [])})
        return {
            "total_documents": len(self.documents),
            "source_files": source_files,
            "tags": tags,
            "index_path": str(self.index_path),
        }


knowledge_query = KnowledgeBaseQuery()


async def query_knowledge_base(
    query: str,
    top_k: int | None = None,
    score_threshold: float | None = None,
) -> Optional[dict[str, Any]]:
    return await knowledge_query.search(query, top_k, score_threshold)


async def search_by_tags(tags: list[str], top_k: int | None = None) -> Optional[dict[str, Any]]:
    return await knowledge_query.search_by_tags(tags, top_k)


def get_knowledge_stats() -> dict[str, Any]:
    return knowledge_query.get_stats()
