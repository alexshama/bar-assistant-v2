"""
Tests for text request routing and handling.
"""

import pytest
from unittest.mock import patch

from services.router import RequestRouter


class TestRequestRouter:
    def setup_method(self):
        self.router = RequestRouter()

    def test_determine_request_type_recipe(self):
        recipe_queries = [
            "рецепт негрони",
            "как приготовить мохито",
            "как сделать мартини",
            "состав маргариты",
            "ингредиенты космополитена",
        ]

        for query in recipe_queries:
            assert self.router._determine_request_type(query.lower()) == "recipe"

    def test_determine_request_type_image(self):
        image_queries = [
            "покажи негрони",
            "сгенерируй изображение мартини",
            "картинка мохито",
            "фото коктейля",
            "покажи как подавать олд фэшн",
        ]

        for query in image_queries:
            assert self.router._determine_request_type(query.lower()) == "image"

    def test_determine_request_type_knowledge(self):
        knowledge_queries = [
            "что такое виски",
            "разница между лагером и элем",
            "как правильно подавать коктейль",
        ]

        for query in knowledge_queries:
            assert self.router._determine_request_type(query.lower()) == "knowledge"

    def test_determine_request_type_general(self):
        general_queries = [
            "привет",
            "как дела",
            "что ты умеешь",
            "расскажи анекдот",
            "какой джин лучше для мартини",
        ]

        for query in general_queries:
            assert self.router._determine_request_type(query.lower()) == "general"

    @patch("rag.query.query_knowledge_base")
    async def test_handle_recipe_request_with_rag(self, mock_rag):
        mock_rag.return_value = {
            "documents": ["Негрони - классический итальянский коктейль..."],
            "sources": [{"chunk_id": "COCKTAIL_001_NEGRONI", "score": 0.95}],
        }

        result = await self.router._handle_recipe_request("рецепт негрони", "подробно")

        assert result["text"]
        assert "негрони" in result["text"].lower()
        assert len(result["sources"]) > 0

    @patch("rag.query.query_knowledge_base")
    @patch("services.openai_client.openai_client.chat")
    async def test_handle_recipe_request_fallback(self, mock_chat, mock_rag):
        mock_rag.return_value = {"documents": [], "sources": []}
        mock_chat.return_value = "Негрони готовится из джина, вермута и кампари..."

        result = await self.router._handle_recipe_request("рецепт экзотического коктейля", "подробно")

        assert result["text"]
        assert "негрони" in result["text"].lower()
        mock_chat.assert_called_once()

    @patch("services.openrouter_client.openrouter_client.generate_image")
    async def test_handle_image_request_success(self, mock_generate):
        mock_generate.return_value = b"fake_image_bytes"

        result = await self.router._handle_image_request("покажи негрони")

        assert result["image_bytes"] == b"fake_image_bytes"
        assert "изображение сгенерировано" in result["text"].lower()

    @patch("services.openrouter_client.openrouter_client.generate_image")
    async def test_handle_image_request_failure(self, mock_generate):
        mock_generate.return_value = None

        result = await self.router._handle_image_request("покажи негрони")

        assert result["image_bytes"] is None
        assert "не удалось" in result["text"].lower()

    def test_prepare_tts_text(self):
        html_text = "<b>Негрони</b> - это <i>классический</i> коктейль 🍸"
        clean_text = self.router._prepare_tts_text(html_text)

        assert "<b>" not in clean_text
        assert "<i>" not in clean_text
        assert "🍸" not in clean_text
        assert "негрони" in clean_text.lower()

    @patch("rag.query.query_knowledge_base")
    @patch("services.openai_client.openai_client.chat")
    async def test_process_request_integration(self, mock_chat, mock_rag):
        mock_rag.return_value = {
            "documents": ["Негрони - классический коктейль..."],
            "sources": [{"chunk_id": "TEST_001", "score": 0.9}],
        }

        result = await self.router.process_request("рецепт негрони", user_id=123, mode="подробно")

        assert result["text"]
        assert result["tts_text"]
        assert "негрони" in result["text"].lower()
        assert len(result["sources"]) > 0


if __name__ == "__main__":
    pytest.main([__file__])
