"""
Request router that maps user intents to the appropriate services.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import rag.query as rag_query
from config import settings
from services.openai_client import openai_client
from services.openrouter_client import openrouter_client
from services.utils import prepare_tts_text

logger = logging.getLogger(__name__)


class RequestRouter:
    def __init__(self) -> None:
        self.recipe_patterns = [
            r"рецепт\s+(.+)",
            r"как\s+приготовить\s+(.+)",
            r"как\s+сделать\s+(.+)",
            r"состав\s+(.+)",
            r"ингредиенты\s+(.+)",
        ]
        self.image_patterns = [
            r"покажи\s+(.+)",
            r"сгенерируй\s+изображение\s+(.+)",
            r"картинка\s+(.+)",
            r"фото\s+(.+)",
            r"изображение\s+(.+)",
            r"покажи\s+как\s+(.+)",
            r"сгенерируй\s+(.+)",
        ]
        self.knowledge_patterns = [
            r"что\s+такое",
            r"чем\s+отличается",
            r"разница\s+между",
            r"как\s+правильно\s+подавать",
            r"какой\s+.+\s+лучше\s+для",
            r"расскажи\s+про",
            r"информация\s+о",
        ]
        self.recommendation_markers = [
            "какой",
            "лучше",
            "что лучше",
            "посоветуй",
            "порекомендуй",
            "рекомендуй",
            "вместо",
            "заменить",
            "подойдет ли",
            "подходит ли",
        ]

    async def process_request(self, text: str, user_id: int, mode: str = "подробно") -> dict[str, Any]:
        del user_id  # Reserved for future personalization.

        cleaned_text = (text or "").strip()
        request_type = self._determine_request_type(cleaned_text.lower())
        logger.info("Routing request '%s' as %s", cleaned_text[:120], request_type)

        result = {"text": "", "tts_text": "", "image_bytes": None, "sources": []}

        try:
            if request_type == "recipe":
                result = await self._handle_recipe_request(cleaned_text, mode)
            elif request_type == "image":
                result = await self._handle_image_request(cleaned_text)
            elif request_type == "knowledge":
                result = await self._handle_knowledge_request(cleaned_text, mode)
            else:
                result = await self._handle_general_request(cleaned_text, mode)
        except Exception as error:
            logger.error("Failed to process request: %s", error)
            result["text"] = "😔 Произошла ошибка при обработке запроса. Попробуйте еще раз."

        result["tts_text"] = prepare_tts_text(result["text"])
        return result

    def _determine_request_type(self, text: str) -> str:
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in self.image_patterns):
            return "image"

        if any(re.search(pattern, text, re.IGNORECASE) for pattern in self.recipe_patterns):
            return "recipe"

        # Recommendation queries should go through the general LLM path with
        # bartender guidance, not through factual RAG snippets about a cocktail.
        if self._is_recommendation_query(text):
            return "general"

        has_knowledge_keywords = any(
            keyword in text
            for keyword in (
                "коктейль",
                "напиток",
                "виски",
                "водка",
                "джин",
                "ром",
                "текила",
                "вино",
                "шампанское",
                "ликер",
                "пиво",
                "лагер",
                "эль",
                "мартини",
                "подавать",
                "гарнир",
                "лед",
            )
        )

        if has_knowledge_keywords and any(re.search(pattern, text, re.IGNORECASE) for pattern in self.knowledge_patterns):
            return "knowledge"

        if has_knowledge_keywords and any(
            marker in text for marker in ("разница", "отличается", "подавать", "лучше для")
        ):
            return "knowledge"

        return "general"

    async def _handle_recipe_request(self, text: str, mode: str) -> dict[str, Any]:
        rag_result = await rag_query.query_knowledge_base(text, top_k=3)
        result = {"text": "", "sources": []}

        if rag_result and rag_result["documents"]:
            result["text"] = self._format_recipe_response(rag_result, mode)
            result["sources"] = rag_result.get("sources", [])
            return result

        ai_response = await openai_client.chat(
            [
                {"role": "system", "content": settings.system_prompt},
                {"role": "user", "content": f"Дай рецепт: {text}"},
            ]
        )
        result["text"] = ai_response or "Извините, не удалось найти рецепт."
        return result

    async def _handle_image_request(self, text: str) -> dict[str, Any]:
        result = {"text": "", "image_bytes": None, "sources": []}
        rag_result = await rag_query.query_knowledge_base(text, top_k=3)

        if rag_result and rag_result["documents"]:
            best_document, best_source = self._select_best_document_for_image(
                rag_result["documents"], rag_result.get("sources", []), text
            )
            result["sources"] = [best_source] if best_source else []
            image_prompt = self._create_cocktail_image_prompt(best_document, text)
            generation_mode = self._determine_image_generation_mode(best_document, text)
            cocktail_id = best_source.get("chunk_id", "unknown") if best_source else "unknown"
            image_bytes = await openrouter_client.generate_image(
                image_prompt,
                cocktail_id,
                generation_mode=generation_mode,
            )

            if image_bytes:
                result["image_bytes"] = image_bytes
                result["text"] = (
                    "🖼 <b>Изображение сгенерировано.</b>\n\n"
                    f"📚 Использован рецепт из базы знаний:\n{best_document}"
                )
            else:
                result["text"] = (
                    "📚 <b>Рецепт найден, но изображение не удалось сгенерировать.</b>\n\n"
                    f"{best_document}"
                )
            return result

        image_bytes = await openrouter_client.generate_image(text)
        if image_bytes:
            result["image_bytes"] = image_bytes
            result["text"] = "🖼 <b>Изображение сгенерировано.</b>\n\nТочного рецепта в базе не найдено."
        else:
            result["text"] = "😔 Не удалось сгенерировать изображение."
        return result

    def _determine_image_generation_mode(self, cocktail_info: str, original_request: str) -> str:
        combined = f"{cocktail_info}\n{original_request}".lower()
        if "b-52" in combined or "b52" in combined:
            return "layered_shot"
        if "слои" in combined and ("шот" in combined or "shot" in combined):
            return "layered_shot"
        return "default"

    def _create_cocktail_image_prompt(self, cocktail_info: str, original_request: str) -> str:
        cocktail_name = self._extract_cocktail_name(cocktail_info, original_request)
        ingredients = self._extract_ingredients(cocktail_info)
        glass_type = self._extract_glass_type(cocktail_info)
        serving = self._extract_serving(cocktail_info)
        garnish = self._extract_garnish(cocktail_info)
        color = self._extract_color_info(cocktail_info)

        if self._determine_image_generation_mode(cocktail_info, original_request) == "layered_shot":
            return self._create_layered_shot_prompt(cocktail_name, cocktail_info)

        if cocktail_name.lower() in {"негрони", "negroni"}:
            return (
                "Professional cocktail photography of one classic Negroni. "
                "Exactly one rocks glass in frame, filled with a deep ruby-red cocktail over large clear ice cubes. "
                "Classic build: gin, Campari, sweet vermouth. "
                "Garnish only with a small orange peel or orange slice on the rim. "
                "Spirit-forward Italian aperitivo style, elegant realistic bar setting, realistic lighting. "
                "No foam, no whipped cream, no creamy topping, no cherry, no mint, no straw, no extra glass, no second drink."
            )

        prompt = f"Professional cocktail photography. Single {cocktail_name} cocktail. "
        prompt += f"Served in one {glass_type}. "
        if color:
            prompt += f"Cocktail color: {color}. "
        if ingredients:
            prompt += f"Made with {ingredients}. "
        if serving:
            prompt += f"{serving}. "
        elif garnish:
            prompt += f"Garnished with {garnish}. "
        prompt += (
            "Single drink in frame, realistic bar background, elegant lighting, no text, "
            "no extra glasses, no second drink, no whipped cream, no foam unless explicitly required, "
            "no excessive decorations, no unrealistic garnish."
        )
        return prompt

    def _create_layered_shot_prompt(self, cocktail_name: str, cocktail_info: str) -> str:
        name_lower = cocktail_name.lower()
        if name_lower in {"b-52", "b52"}:
            return (
                "Professional cocktail photography of one B-52 layered shot. "
                "Exactly one small clear straight-sided shot glass in frame. "
                "Strict layered shot mode. Side profile only, with the full height of the glass visible. "
                "Exactly three horizontal liquid layers only, no more and no fewer. "
                "From bottom to top in this exact order: "
                "1) dark brown coffee liqueur, "
                "2) light beige cream liqueur, "
                "3) transparent orange-golden triple sec. "
                "Each layer should occupy roughly one third of the glass height. "
                "Sharp clean separation between layers, no mixed gradients, no repeated bands, no fourth layer. "
                "No floating foam, no creamy cap, no garnish, no straw, no bottle, no hands, "
                "no extra glass, no second drink, plain neutral bar background, realistic studio lighting."
            )

        ingredients = self._extract_ingredients(cocktail_info)
        return (
            f"Professional cocktail photography of one layered shot: {cocktail_name}. "
            "Exactly one small clear shot glass in frame. Strict layered shot mode. "
            "Side profile only, with clearly separated horizontal layers and realistic liquid density. "
            f"Ingredients reference: {ingredients}. "
            "No extra drink, no garnish, no straw, no foam cap, no repeated bands, plain neutral background."
        )

    def _extract_cocktail_name(self, info: str, original: str) -> str:
        match = re.search(r"COCKTAIL_\d+_([A-Z0-9_]+)", info.upper())
        if match:
            return match.group(1).replace("_", " ").title()

        lower_info = info.lower()
        lower_original = original.lower()
        for name in (
            "негрони",
            "мартини",
            "мохито",
            "маргарита",
            "дайкири",
            "манхэттен",
            "b-52",
            "космополитен",
            "олд фэшн",
            "виски сауэр",
        ):
            if name in lower_info or name in lower_original:
                return name.title()
        return "cocktail"

    def _extract_ingredients(self, info: str) -> str:
        mapping = {
            "джин": "gin",
            "gin": "gin",
            "водка": "vodka",
            "vodka": "vodka",
            "ром": "rum",
            "rum": "rum",
            "виски": "whiskey",
            "whiskey": "whiskey",
            "кампари": "Campari",
            "campari": "Campari",
            "вермут": "vermouth",
            "vermouth": "vermouth",
            "лайм": "lime",
            "lime": "lime",
            "лимон": "lemon",
            "lemon": "lemon",
            "coffee liqueur": "coffee liqueur",
            "кофейный ликёр": "coffee liqueur",
            "cream liqueur": "cream liqueur",
            "сливочный ликёр": "cream liqueur",
            "triple sec": "triple sec",
        }
        found = [value for marker, value in mapping.items() if marker in info.lower()]
        unique = list(dict.fromkeys(found))
        return ", ".join(unique) if unique else "premium spirits"

    def _extract_glass_type(self, info: str) -> str:
        info_lower = info.lower()
        if any(marker in info_lower for marker in ("мартини", "купе")):
            return "martini glass"
        if any(marker in info_lower for marker in ("рокс", "олд фэшн", "rocks")):
            return "rocks glass"
        if any(marker in info_lower for marker in ("хайбол", "highball")):
            return "highball glass"
        if any(marker in info_lower for marker in ("шот", "shot")):
            return "shot glass"
        return "appropriate cocktail glass"

    def _extract_serving(self, info: str) -> str:
        match = re.search(r"Подача:\s*([^.]+)", info, re.IGNORECASE)
        if not match:
            return ""
        serving = match.group(1).strip()
        return serving.replace("апельсин", "orange slice").replace("лимон", "lemon slice")

    def _extract_garnish(self, info: str) -> str:
        garnishes = []
        info_lower = info.lower()
        if "апельсин" in info_lower or "orange" in info_lower:
            garnishes.append("orange slice")
        if "цедра" in info_lower or "twist" in info_lower:
            garnishes.append("lemon twist")
        if "оливка" in info_lower or "olive" in info_lower:
            garnishes.append("olive")
        if "вишня" in info_lower or "cherry" in info_lower:
            garnishes.append("cherry")
        if "мята" in info_lower or "mint" in info_lower:
            garnishes.append("fresh mint")
        return ", ".join(dict.fromkeys(garnishes))

    def _extract_color_info(self, info: str) -> str:
        info_lower = info.lower()
        explicit_map = {
            "красн": "red",
            "red": "red",
            "золот": "golden",
            "golden": "golden",
            "прозрачн": "clear",
            "clear": "clear",
            "янтарн": "amber",
            "amber": "amber",
            "зелен": "green",
            "green": "green",
        }
        for marker, color in explicit_map.items():
            if marker in info_lower:
                return color

        ingredient_colors = {
            "кампари": "bright red",
            "campari": "bright red",
            "cranberry": "cranberry red",
            "клюквен": "cranberry red",
            "midori": "bright green",
            "мидори": "bright green",
            "limoncello": "bright yellow",
            "лимончелло": "bright yellow",
            "coffee liqueur": "dark brown",
            "кофейный ликёр": "dark brown",
            "виски": "golden amber",
            "whiskey": "golden amber",
            "vodka": "clear",
            "водка": "clear",
            "джин": "clear",
            "gin": "clear",
        }
        for marker, color in ingredient_colors.items():
            if marker in info_lower:
                return color

        if "слои" in info_lower or "layered" in info_lower:
            return "layered with distinct color layers"
        return "golden"

    def _select_best_document_for_image(self, documents: list[str], sources: list[dict], query: str) -> tuple[str, dict]:
        if len(documents) == 1:
            return documents[0], sources[0] if sources else {}

        query_keywords = self._extract_query_keywords(query.lower())
        best_doc = documents[0]
        best_source = sources[0] if sources else {}
        best_score = -1

        for index, (document, source) in enumerate(zip(documents, sources)):
            score = 20 if index == 0 else 0
            chunk_id = source.get("chunk_id", "").lower()
            document_lower = document.lower()

            for keyword in query_keywords:
                if keyword in chunk_id:
                    score += 15
                if keyword in document_lower:
                    score += 5
                for source_keyword in source.get("keywords", []):
                    if keyword in str(source_keyword).lower():
                        score += 3

            if score > best_score:
                best_score = score
                best_doc = document
                best_source = source

        return best_doc, best_source

    def _extract_query_keywords(self, query: str) -> list[str]:
        stop_words = {
            "покажи",
            "сгенерируй",
            "картинку",
            "фото",
            "изображение",
            "как",
            "выглядит",
            "что",
            "делать",
            "и",
        }
        special_patterns = {
            "лонг айленд айс ти": ["long", "island", "iced", "tea", "long_island_iced_tea"],
            "б-52": ["b-52", "b52", "52"],
            "b-52": ["b-52", "b52", "52"],
            "b52": ["b-52", "b52", "52"],
            "олд фэшн": ["old", "fashioned", "old_fashioned"],
            "мартини": ["martini"],
            "негрони": ["negroni"],
        }
        for pattern, replacements in special_patterns.items():
            if pattern in query:
                return replacements

        keywords = []
        forms = {
            "маргариты": "маргарита",
            "манхэттена": "манхэттен",
            "космополитена": "космополитен",
        }
        for word in query.split():
            if len(word) <= 1 or word in stop_words:
                continue
            base_word = forms.get(word.lower(), word.lower())
            keywords.append(base_word)
            if word.lower() in {"b-52", "b52", "б-52", "б52"}:
                keywords.extend(["b-52", "b52", "52"])
        return keywords

    async def _handle_knowledge_request(self, text: str, mode: str) -> dict[str, Any]:
        top_k = 1 if self._is_specific_question(text) else 3
        rag_result = await rag_query.query_knowledge_base(text, top_k=top_k)

        if rag_result and rag_result["documents"]:
            return {
                "text": self._format_knowledge_response(rag_result, mode),
                "sources": rag_result.get("sources", []),
            }

        fallback = await self._handle_general_request(text, mode)
        fallback["text"] = "ℹ️ В базе знаний нет точных данных по вашему запросу.\n\n" + fallback["text"]
        return fallback

    def _is_specific_question(self, text: str) -> bool:
        text_lower = text.lower()
        specific_patterns = [
            r"что такое \w+",
            r"что это \w+",
            r"определение \w+",
            r"объясни что такое \w+",
            r"расскажи про \w+$",
        ]
        if any(re.search(pattern, text_lower) for pattern in specific_patterns):
            return True

        specific_drinks = [
            "виски",
            "whisky",
            "whiskey",
            "водка",
            "vodka",
            "джин",
            "gin",
            "ром",
            "rum",
            "текила",
            "tequila",
            "коньяк",
            "cognac",
            "бренди",
            "brandy",
            "ликёр",
            "liqueur",
            "пилснер",
            "pilsner",
            "лагер",
            "lager",
            "эль",
            "ale",
        ]
        return len([drink for drink in specific_drinks if drink in text_lower]) == 1

    async def _handle_general_request(self, text: str, mode: str) -> dict[str, Any]:
        system_prompt = settings.system_prompt
        if mode == "кратко":
            system_prompt += " Отвечай максимально кратко и по существу."

        rag_context = ""
        if self._is_recommendation_query(text):
            rag_result = await rag_query.query_knowledge_base(text, top_k=2)
            if rag_result and rag_result.get("documents"):
                rag_context = "\n\nКонтекст из базы знаний:\n" + "\n\n".join(rag_result["documents"][:2])

            system_prompt += (
                " Если пользователь спрашивает, какой спиртной напиток, ингредиент или бренд лучше подойдет "
                "для конкретного коктейля или ситуации, не давай рецепт коктейля, если его не просили явно. "
                "Нужно ответить как бармен-консультант: предложи 2-3 варианта, объясни разницу по сухости, "
                "ароматике, стилю и уместности. Если запрос про джин для мартини, говори именно о выборе джина, "
                "а не о рецепте коктейля мартини."
            )

        ai_response = await openai_client.chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text + rag_context},
            ]
        )
        return {
            "text": ai_response or "Извините, не удалось обработать ваш запрос.",
            "sources": [],
        }

    def _is_recommendation_query(self, text: str) -> bool:
        text_lower = text.lower()
        has_recommendation_marker = any(marker in text_lower for marker in self.recommendation_markers)
        has_target_context = any(
            marker in text_lower
            for marker in ("для", "вместо", "к мартини", "коктейль", "напиток", "джин", "виски", "ром", "водка")
        )
        return has_recommendation_marker and has_target_context

    def _format_recipe_response(self, rag_result: dict, mode: str) -> str:
        documents = rag_result["documents"]
        sources = rag_result.get("sources", [])
        response = "🍹 <b>Рецепт найден в базе знаний:</b>\n\n" + "\n\n".join(documents)
        if sources and mode == "подробно":
            response += "\n\n<i>Источники: " + ", ".join(source.get("chunk_id", "unknown") for source in sources[:3]) + "</i>"
        return response

    def _format_knowledge_response(self, rag_result: dict, mode: str) -> str:
        documents = rag_result["documents"]
        sources = rag_result.get("sources", [])
        response = "📚 <b>Информация из базы знаний:</b>\n\n" + "\n\n".join(documents)
        if sources and mode == "подробно":
            response += "\n\n<i>Источники: " + ", ".join(source.get("chunk_id", "unknown") for source in sources[:3]) + "</i>"
        return response

    def _prepare_tts_text(self, html_text: str) -> str:
        return prepare_tts_text(html_text)


request_router = RequestRouter()


async def process_text_request(text: str, user_id: int, mode: str = "подробно") -> dict[str, Any]:
    return await request_router.process_request(text, user_id, mode)
