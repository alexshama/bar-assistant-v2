"""
Роутер запросов - определяет тип запроса и направляет к нужному сервису
"""

import logging
import re
from typing import Dict, Any, Optional, List

from rag.query import query_knowledge_base
from services.openai_client import openai_client
from services.openrouter_client import openrouter_client
from config import settings

logger = logging.getLogger(__name__)


class RequestRouter:
    """Роутер для обработки различных типов запросов"""
    
    def __init__(self):
        # Паттерны для определения типа запроса
        self.recipe_patterns = [
            r'рецепт\s+(.+)',
            r'как\s+приготовить\s+(.+)',
            r'как\s+сделать\s+(.+)',
            r'состав\s+(.+)',
            r'ингредиенты\s+(.+)'
        ]
        
        self.image_patterns = [
            r'покажи\s+(.+)',
            r'сгенерируй\s+изображение\s+(.+)',
            r'картинка\s+(.+)',
            r'фото\s+(.+)',
            r'изображение\s+(.+)',
            r'покажи\s+как\s+(.+)',
            r'сгенерируй\s+(.+)'
        ]
    
    async def process_request(
        self, 
        text: str, 
        user_id: int, 
        mode: str = "подробно"
    ) -> Dict[str, Any]:
        """Основная функция обработки запроса"""
        
        text_lower = text.lower().strip()
        
        # Определяем тип запроса
        request_type = self._determine_request_type(text_lower)
        
        logger.info(f"РОУТИНГ: '{text[:100]}...' -> {request_type}")
        
        # Дополнительное логирование для отладки
        if request_type == "general":
            logger.info("  -> Запрос отправлен к OpenAI GPT-4 для рассуждения")
        elif request_type == "knowledge":
            logger.info("  -> Запрос отправлен к RAG базе знаний")
        elif request_type == "recipe":
            logger.info("  -> Запрос на рецепт отправлен к RAG")
        elif request_type == "image":
            logger.info("  -> Запрос на изображение")
        
        result = {
            "text": "",
            "tts_text": "",
            "image_bytes": None,
            "sources": []
        }
        
        try:
            if request_type == "recipe":
                result = await self._handle_recipe_request(text, mode)
            elif request_type == "image":
                result = await self._handle_image_request(text)
            elif request_type == "knowledge":
                result = await self._handle_knowledge_request(text, mode)
            else:
                result = await self._handle_general_request(text, mode)
                
        except Exception as e:
            logger.error(f"Ошибка при обработке запроса: {e}")
            result["text"] = "😔 Произошла ошибка при обработке запроса. Попробуйте еще раз."
        
        # Подготавливаем текст для TTS (убираем HTML теги)
        result["tts_text"] = self._prepare_tts_text(result["text"])
        
        return result
    
    def _determine_request_type(self, text: str) -> str:
        """Определение типа запроса"""
        
        # Проверяем запросы на изображения
        for pattern in self.image_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return "image"
        
        # Проверяем запросы рецептов
        for pattern in self.recipe_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return "recipe"
        
        # ПРИОРИТЕТ: Проверяем вопросы, требующие рассуждения (должны идти к OpenAI)
        # Расширенные паттерны для вопросов-рассуждений
        reasoning_patterns = [
            r'какой\s+\w*\s*лучше',
            r'что\s+лучше',
            r'лучше\s+предложить',
            r'лучше\s+выбрать',
            r'лучше\s+взять',
            r'посоветуй',
            r'посоветовать',
            r'рекомендуй',
            r'рекомендовать',
            r'порекомендуй',
            r'вместо\s+\w+',
            r'заменить\s+на',
            r'альтернатива',
            r'сравни',
            r'сравнить',
            r'отличие',
            r'разница',
            r'чем\s+отличается',
            r'в\s+чем\s+разница',
            r'стоит\s+ли',
            r'можно\s+ли\s+заменить',
            r'что\s+выбрать',
            r'как\s+выбрать',
            r'какой\s+предпочесть',
            r'предпочтительнее',
            r'оптимальн',
            r'подходящ',
            r'подойдет\s+ли',
            r'подходит\s+ли',
            r'мнение',
            r'твое\s+мнение',
            r'как\s+думаешь',
            r'как\s+считаешь',
            r'стоит\s+попробовать',
            r'попробовать\s+ли'
        ]
        
        # ВАЖНО: Проверяем рассуждения ПЕРВЫМИ, до проверки ключевых слов
        for pattern in reasoning_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.info(f"✓ ПАТТЕРН РАССУЖДЕНИЯ: '{pattern}' найден в тексте -> OpenAI")
                return "general"  # Отправляем к OpenAI для рассуждения
        
        # Проверяем ключевые слова для поиска в базе знаний (только для фактических запросов)
        knowledge_keywords = [
            'коктейль', 'коктейля', 'коктейлей', 'коктейлю', 'коктейлем',
            'напиток', 'напитка', 'напитков', 'напитку', 'напитком',
            'алкоголь', 'алкоголя', 'пиво', 'пива', 
            'виски', 'водка', 'водки', 'джин', 'джина', 'ром', 'рома',
            'текила', 'текилы', 'вино', 'вина', 'шампанское', 'шампанского',
            'ликер', 'ликера', 'ликеры', 'ликеров',
            'бар', 'бара', 'бармен', 'бармена', 'подача', 'подачи', 
            'гарнир', 'гарнира', 'лед', 'льда'
        ]
        
        # Проверяем, что это именно фактический запрос, а не вопрос для рассуждения
        factual_patterns = [
            r'что\s+такое',
            r'определение\s+\w+',
            r'определение',
            r'объясни\s+что\s+такое',
            r'расскажи\s+про',
            r'информация\s+о',
            r'история\s+\w+',
            r'происхождение\s+\w+',
            r'состав\s+\w+',
            r'из\s+чего\s+делают'
        ]
        
        is_factual = any(re.search(pattern, text, re.IGNORECASE) for pattern in factual_patterns)
        has_keywords = any(keyword in text.lower() for keyword in knowledge_keywords)
        
        if has_keywords and is_factual:
            logger.info(f"✓ ФАКТИЧЕСКИЙ ЗАПРОС: ключевые слова + фактический паттерн -> RAG")
            return "knowledge"
        elif has_keywords and not is_factual:
            # Если есть ключевые слова, но это не фактический запрос, отправляем к OpenAI
            logger.info(f"✓ КЛЮЧЕВЫЕ СЛОВА БЕЗ ФАКТИЧЕСКОГО ПАТТЕРНА -> OpenAI")
            return "general"
        
        # По умолчанию отправляем к OpenAI для общих вопросов
        logger.info(f"✓ ОБЩИЙ ЗАПРОС: нет специфических паттернов -> OpenAI")
        return "general"
    
    async def _handle_recipe_request(self, text: str, mode: str) -> Dict[str, Any]:
        """Обработка запросов рецептов"""
        
        # Сначала ищем в базе знаний
        rag_result = await query_knowledge_base(text, top_k=3)
        
        result = {"text": "", "sources": []}
        
        if rag_result and rag_result["documents"]:
            # Формируем структурированный ответ на основе RAG
            recipe_text = self._format_recipe_response(rag_result, mode)
            result["text"] = recipe_text
            result["sources"] = rag_result.get("sources", [])
        else:
            # Fallback к OpenAI если в RAG нет данных
            messages = [
                {"role": "system", "content": settings.system_prompt},
                {"role": "user", "content": f"Дай рецепт: {text}"}
            ]
            
            ai_response = await openai_client.chat(messages)
            result["text"] = ai_response or "Извините, не удалось найти рецепт."
        
        return result
    
    async def _handle_image_request(self, text: str) -> Dict[str, Any]:
        """Обработка запросов на генерацию изображений с поиском в базе"""
        
        result = {"text": "", "image_bytes": None, "sources": []}
        
        # Сначала ищем информацию о коктейле в базе знаний
        logger.info("Ищем информацию о коктейле в базе знаний...")
        rag_result = await query_knowledge_base(text, top_k=3)
        
        if rag_result and rag_result["documents"]:
            # Нашли информацию в базе - выбираем наиболее релевантный документ
            best_document, best_source = self._select_best_document_for_image(
                rag_result["documents"], 
                rag_result.get("sources", []), 
                text
            )
            
            # Устанавливаем источники только для выбранного документа
            result["sources"] = [best_source] if best_source else []
            
            # Формируем текстовый ответ ТОЛЬКО для выбранного коктейля (не показываем лишние)
            result["text"] = f"📚 <b>Информация из базы знаний:</b>\n\n{best_document}"
            
            # Добавляем источник только выбранного коктейля
            if best_source:
                source_id = best_source.get("chunk_id", "неизвестно")
                result["text"] += f"\n\n<i>Источник: {source_id}</i>"
            
            # Создаем промпт для изображения на основе НАИБОЛЕЕ РЕЛЕВАНТНОГО документа
            image_prompt = self._create_cocktail_image_prompt(best_document, text)
            
            # Извлекаем ID коктейля для кэширования
            cocktail_id = best_source.get("chunk_id", "unknown") if best_source else "unknown"
            
            # Генерируем изображение
            cocktail_name = self._extract_cocktail_name(best_document, text)
            logger.info(f"Генерируем изображение для {cocktail_name} на основе найденного рецепта...")
            image_bytes = await openrouter_client.generate_image(image_prompt, cocktail_id)
            
            if image_bytes:
                result["image_bytes"] = image_bytes
            else:
                result["text"] += "\n\n😔 Не удалось сгенерировать изображение коктейля."
        
        else:
            # Не нашли в базе - генерируем общее изображение
            logger.info("Информация не найдена в базе, генерируем общее изображение...")
            result["text"] = "ℹ️ Точной информации о коктейле в базе знаний нет.\n\nГенерирую общее изображение..."
            
            image_bytes = await openrouter_client.generate_image(text)
            
            if image_bytes:
                result["image_bytes"] = image_bytes
            else:
                result["text"] = "😔 Не удалось найти информацию о коктейле и сгенерировать изображение."
        
        return result
    
    def _create_cocktail_image_prompt(self, cocktail_info: str, original_request: str) -> str:
        """Создание промпта для изображения на основе информации о коктейле"""
        
        # Извлекаем ключевую информацию из описания коктейля (БЕЗ вкуса!)
        cocktail_name = self._extract_cocktail_name(cocktail_info, original_request)
        ingredients = self._extract_ingredients(cocktail_info)
        glass_type = self._extract_glass_type(cocktail_info)
        serving = self._extract_serving(cocktail_info)  # СТРОГО подача из рецепта
        garnish = self._extract_garnish(cocktail_info)
        color = self._extract_color_info(cocktail_info)
        
        # Специальный промпт только для B-52 (слоистый коктейль)
        if cocktail_name.lower() in ['b-52', 'b52']:
            return ("B-52 layered shot cocktail in small clear shot glass. "
                   "Three distinct horizontal liquid layers: "
                   "Bottom layer: dark brown coffee liqueur. "
                   "Middle layer: light tan cream liqueur. "
                   "Top layer: clear transparent liqueur. "
                   "Clean separation between layers. "
                   "Flat liquid surface on top, no foam or cream. "
                   "Professional bar photography, elegant lighting.")
        
        # Универсальный промпт для всех остальных коктейлей
        prompt = f"Professional cocktail photography. Single {cocktail_name} cocktail. "
        
        # Тип стакана
        if glass_type:
            prompt += f"Served in one {glass_type} only. "
        else:
            prompt += "Served in appropriate cocktail glass. "
        
        # Цвет коктейля (важно для правильного отображения)
        if color and color != 'golden':
            prompt += f"Cocktail color: {color}. "
        
        # Ингредиенты для контекста
        if ingredients:
            prompt += f"Made with {ingredients}. "
        
        # Подача и гарнир СТРОГО из рецепта
        if serving:
            prompt += f"{serving}. "
        elif garnish:
            prompt += f"Garnished with {garnish}. "
        
        # Строгие ограничения против артефактов
        prompt += ("Clean composition with SINGLE cocktail glass only. "
                  "NO extra glasses, NO ice buckets, NO additional items, NO multiple drinks. "
                  "Professional bar background, elegant lighting, realistic style, no text.")
        
        # Дополнительные ограничения для проблемных элементов
        prompt += " NO whipped cream, NO foam on top, NO extra decorations."
        
        return prompt
    
    def _extract_cocktail_name(self, info: str, original: str) -> str:
        """Извлечение названия коктейля"""
        # Сначала пытаемся извлечь из ID чанка (наиболее точно)
        import re
        chunk_id_match = re.search(r'COCKTAIL_\d+_([A-Z_]+)', info.upper())
        if chunk_id_match:
            cocktail_id = chunk_id_match.group(1)
            # Преобразуем ID в читаемое название
            name_mapping = {
                'MARGARITA': 'Margarita',
                'B-52': 'B-52',
                'OLD_FASHIONED': 'Old Fashioned',
                'WHISKEY_SOUR': 'Whiskey Sour',
                'MANHATTAN': 'Manhattan',
                'MARTINI': 'Martini',
                'NEGRONI': 'Negroni',
                'MOJITO': 'Mojito',
                'DAIQUIRI': 'Daiquiri',
                'COSMOPOLITAN': 'Cosmopolitan',
                'LONG_ISLAND_ICED_TEA': 'Long Island Iced Tea'
            }
            if cocktail_id in name_mapping:
                return name_mapping[cocktail_id]
            else:
                # Для неизвестных ID преобразуем подчеркивания в пробелы
                return cocktail_id.replace('_', ' ').title()
        
        # Если не нашли в ID, ищем в тексте и запросе
        info_lower = info.lower()
        original_lower = original.lower()
        
        common_cocktails = [
            'негрони', 'мартини', 'мохито', 'маргарита', 'дайкири', 
            'манхэттен', 'b-52', 'космополитен', 'олд фэшн', 'виски сауэр'
        ]
        
        for name in common_cocktails:
            if name in info_lower or name in original_lower:
                return name.title()
        
        return "cocktail"
    
    def _extract_ingredients(self, info: str) -> str:
        """Извлечение ингредиентов"""
        info_lower = info.lower()
        
        ingredients = []
        if 'джин' in info_lower or 'gin' in info_lower:
            ingredients.append('gin')
        if 'водка' in info_lower or 'vodka' in info_lower:
            ingredients.append('vodka')
        if 'ром' in info_lower or 'rum' in info_lower:
            ingredients.append('rum')
        if 'виски' in info_lower or 'whiskey' in info_lower:
            ingredients.append('whiskey')
        if 'кампари' in info_lower or 'campari' in info_lower:
            ingredients.append('Campari')
        if 'вермут' in info_lower or 'vermouth' in info_lower:
            ingredients.append('vermouth')
        if 'лайм' in info_lower or 'lime' in info_lower:
            ingredients.append('lime')
        if 'лимон' in info_lower or 'lemon' in info_lower:
            ingredients.append('lemon')
        # Специальные ингредиенты для B-52
        if 'кофейный ликёр' in info_lower or 'coffee liqueur' in info_lower:
            ingredients.append('coffee liqueur')
        if 'сливочный ликёр' in info_lower or 'cream liqueur' in info_lower:
            ingredients.append('cream liqueur')
        if 'triple sec' in info_lower:
            ingredients.append('triple sec')
        
        return ', '.join(ingredients) if ingredients else 'premium spirits'
    
    def _extract_glass_type(self, info: str) -> str:
        """Извлечение типа стекла"""
        info_lower = info.lower()
        
        if 'мартини' in info_lower or 'купе' in info_lower:
            return 'martini glass'
        elif 'рокс' in info_lower or 'олд фэшн' in info_lower or 'rocks' in info_lower:
            return 'rocks glass'
        elif 'хайбол' in info_lower or 'highball' in info_lower:
            return 'highball glass'
        elif 'шот' in info_lower or 'shot' in info_lower:
            return 'shot glass'
        
        return 'appropriate cocktail glass'
    
    def _extract_serving(self, info: str) -> str:
        """Извлечение информации о подаче из рецепта"""
        import re
        # Ищем "Подача:" в тексте
        match = re.search(r'Подача:\s*([^.]+)', info, re.IGNORECASE)
        if match:
            serving = match.group(1).strip()
            # Заменяем "апельсин" на "orange slice" (долька, не целый фрукт)
            serving = serving.replace('апельсин', 'orange slice')
            serving = serving.replace('лимон', 'lemon slice')
            return serving
        return ''
    
    def _extract_garnish(self, info: str) -> str:
        """Извлечение информации о гарнире"""
        info_lower = info.lower()
        
        garnishes = []
        if 'апельсин' in info_lower or 'orange' in info_lower:
            garnishes.append('orange slice')  # Долька, не целый фрукт
        if 'лимон' in info_lower and 'цедра' in info_lower:
            garnishes.append('lemon twist')
        if 'оливка' in info_lower or 'olive' in info_lower:
            garnishes.append('olive')
        if 'вишня' in info_lower or 'cherry' in info_lower:
            garnishes.append('cherry')
        if 'мята' in info_lower or 'mint' in info_lower:
            garnishes.append('fresh mint')
        
        return ', '.join(garnishes) if garnishes else ''
    
    def _extract_color_info(self, info: str) -> str:
        """Извлечение информации о цвете на основе ингредиентов"""
        info_lower = info.lower()
        
        # Сначала проверяем явные указания цвета в описании
        if 'красн' in info_lower or 'red' in info_lower:
            return 'red'
        elif 'золот' in info_lower or 'golden' in info_lower:
            return 'golden'
        elif 'прозрачн' in info_lower or 'clear' in info_lower:
            return 'clear'
        elif 'янтарн' in info_lower or 'amber' in info_lower:
            return 'amber'
        elif 'зелен' in info_lower or 'green' in info_lower:
            return 'green'
        
        # Анализируем ингредиенты для определения цвета
        color_ingredients = {
            # Красные/розовые ингредиенты
            'гренадин': 'pink-red',
            'grenadine': 'pink-red',
            'кампари': 'bright red',
            'campari': 'bright red',
            'вишнёвый ликёр': 'cherry red',
            'cherry liqueur': 'cherry red',
            'клюквенный': 'cranberry red',
            'cranberry': 'cranberry red',
            'красное вино': 'deep red',
            'red wine': 'deep red',
            
            # Зеленые ингредиенты
            'мидори': 'bright green',
            'midori': 'bright green',
            'абсент': 'green',
            'absinthe': 'green',
            
            # Желтые/золотистые
            'лимончелло': 'bright yellow',
            'limoncello': 'bright yellow',
            'шартрез': 'yellow-green',
            'chartreuse': 'yellow-green',
            'куантро': 'golden',
            'cointreau': 'golden',
            
            # Коричневые/темные
            'кофейный ликёр': 'dark brown',
            'coffee liqueur': 'dark brown',
            'амаретто': 'amber',
            'amaretto': 'amber',
            'виски': 'golden amber',
            'whiskey': 'golden amber',
            'whisky': 'golden amber',
            'коньяк': 'amber',
            'cognac': 'amber',
            'ром': 'golden',
            'rum': 'golden',
            
            # Прозрачные
            'водка': 'clear',
            'vodka': 'clear',
            'джин': 'clear',
            'gin': 'clear',
            'triple sec': 'clear',
            'трипл сек': 'clear'
        }
        
        # Ищем цветообразующие ингредиенты
        for ingredient, color in color_ingredients.items():
            if ingredient in info_lower:
                return color
        
        # Специальные случаи для слоистых коктейлей
        if 'слои' in info_lower or 'layered' in info_lower:
            return 'layered with distinct color layers'
        elif 'кофейн' in info_lower and 'сливочн' in info_lower:
            return 'layered brown and cream colors'
        
        # Если ничего не найдено, возвращаем нейтральный цвет
        return 'golden'
    
    def _select_best_document_for_image(self, documents: List[str], sources: List[Dict], query: str) -> tuple:
        """Выбирает наиболее релевантный документ для генерации изображения"""
        
        if len(documents) == 1:
            return documents[0], sources[0] if sources else {}
        
        query_lower = query.lower()
        best_score = -1
        best_doc = documents[0]
        best_source = sources[0] if sources else {}
        
        logger.info(f"Выбираем лучший документ из {len(documents)} для запроса: {query}")
        
        # Ищем наиболее релевантный документ
        for i, (doc, source) in enumerate(zip(documents, sources)):
            score = 0
            doc_lower = doc.lower()
            chunk_id = source.get('chunk_id', '').lower()
            
            # Извлекаем ключевые слова из запроса
            query_keywords = self._extract_query_keywords(query_lower)
            
            logger.info(f"Документ {i}: {chunk_id}, ключевые слова запроса: {query_keywords}")
            
            # Если это первый документ (наиболее релевантный по RAG), даем ему бонус
            if i == 0:
                score += 20
                logger.info(f"  +20 за первое место в RAG поиске")
            
            for keyword in query_keywords:
                # Высокий приоритет совпадению в ID чанка
                if keyword in chunk_id:
                    score += 15
                    logger.info(f"  +15 за совпадение '{keyword}' в ID")
                
                # Средний приоритет совпадению в тексте
                if keyword in doc_lower:
                    score += 5
                    logger.info(f"  +5 за совпадение '{keyword}' в тексте")
                
                # Проверяем ключевые слова источника
                source_keywords = source.get('keywords', [])
                if isinstance(source_keywords, list):
                    for src_keyword in source_keywords:
                        if keyword in str(src_keyword).lower():
                            score += 3
                            logger.info(f"  +3 за совпадение '{keyword}' в ключевых словах")
            
            # Дополнительная проверка для точных совпадений названий коктейлей
            cocktail_names = ['b-52', 'b52', 'негрони', 'мартини', 'мохито', 'маргарита']
            for cocktail in cocktail_names:
                if cocktail in query_lower and cocktail.replace('-', '') in chunk_id.replace('_', '').replace('-', ''):
                    score += 25
                    logger.info(f"  +25 за точное совпадение названия коктейля '{cocktail}'")
            
            logger.info(f"  Итоговый счет для {chunk_id}: {score}")
            
            if score > best_score:
                best_score = score
                best_doc = doc
                best_source = source
        
        logger.info(f"Выбран документ: {best_source.get('chunk_id', 'unknown')} с счетом {best_score}")
        return best_doc, best_source
    
    def _extract_query_keywords(self, query: str) -> List[str]:
        """Извлекает ключевые слова из запроса пользователя"""
        
        # Убираем служебные слова
        stop_words = ['покажи', 'сгенерируй', 'картинку', 'фото', 'изображение', 'как', 'выглядит', 'что', 'делать', 'и']
        
        words = query.split()
        keywords = []
        
        # Словарь склонений для коктейлей
        cocktail_forms = {
            'маргариты': 'маргарита',
            'негрони': 'негрони', 
            'мартини': 'мартини',
            'мохито': 'мохито',
            'дайкири': 'дайкири',
            'манхэттена': 'манхэттен',
            'космополитена': 'космополитен'
        }
        
        # Сначала проверяем специальные паттерны (составные названия)
        special_patterns = {
            'лонг айленд айс ти': ['long', 'island', 'iced', 'tea', 'long_island_iced_tea'],
            'лонг айленд': ['long', 'island', 'long_island'],
            'айс ти': ['iced', 'tea', 'iced_tea'],
            'б-52': ['b-52', 'b52', '52'],
            'b-52': ['b-52', 'b52', '52'],
            'b52': ['b-52', 'b52', '52'],
            'олд фэшн': ['old', 'fashioned', 'old_fashioned'],
            'мартини': ['martini'],
            'негрони': ['negroni']
        }
        
        # Ищем точные совпадения составных названий
        found_special = False
        for pattern, replacements in special_patterns.items():
            if pattern in query:
                keywords.extend(replacements)
                found_special = True
                break
        
        # Если не нашли специальные паттерны, разбираем по словам
        if not found_special:
            for word in words:
                if len(word) > 1 and word not in stop_words:
                    # Приводим к базовой форме если есть в словаре
                    base_word = cocktail_forms.get(word.lower(), word)
                    keywords.append(base_word)
                    
                    # Добавляем варианты для B-52
                    if word.lower() in ['b-52', 'b52', 'б-52', 'б52']:
                        keywords.extend(['b-52', 'b52', '52'])
        
        return keywords
    
    async def _handle_knowledge_request(self, text: str, mode: str) -> Dict[str, Any]:
        """Обработка запросов к базе знаний"""
        
        # Для конкретных вопросов ограничиваем количество результатов
        top_k = 1 if self._is_specific_question(text) else 3
        
        rag_result = await query_knowledge_base(text, top_k=top_k)
        
        result = {"text": "", "sources": []}
        
        if rag_result and rag_result["documents"]:
            # Формируем ответ на основе найденной информации
            knowledge_text = self._format_knowledge_response(rag_result, mode)
            result["text"] = knowledge_text
            result["sources"] = rag_result.get("sources", [])
        else:
            # Fallback к OpenAI
            result = await self._handle_general_request(text, mode)
            result["text"] = "ℹ️ В базе знаний нет точных данных по вашему запросу.\n\n" + result["text"]
        
        return result
    
    def _is_specific_question(self, text: str) -> bool:
        """Определяет, является ли вопрос конкретным (требует один точный ответ)"""
        text_lower = text.lower()
        
        # Вопросы типа "что такое X?"
        specific_patterns = [
            r'что такое \w+',
            r'что это \w+',
            r'определение \w+',
            r'объясни что такое \w+',
            r'расскажи про \w+$',  # Конкретно про что-то одно
        ]
        
        import re
        for pattern in specific_patterns:
            if re.search(pattern, text_lower):
                return True
        
        # Конкретные названия напитков
        specific_drinks = [
            'виски', 'whisky', 'whiskey',
            'водка', 'vodka', 
            'джин', 'gin',
            'ром', 'rum',
            'текила', 'tequila',
            'коньяк', 'cognac',
            'бренди', 'brandy',
            'ликёр', 'liqueur',
            'пилснер', 'pilsner',
            'лагер', 'lager',
            'эль', 'ale'
        ]
        
        # Если в вопросе упоминается только один конкретный напиток
        mentioned_drinks = [drink for drink in specific_drinks if drink in text_lower]
        if len(mentioned_drinks) == 1:
            return True
        
        return False
    
    async def _handle_general_request(self, text: str, mode: str) -> Dict[str, Any]:
        """Обработка общих запросов через OpenAI"""
        
        system_prompt = settings.system_prompt
        if mode == "кратко":
            system_prompt += " Отвечай максимально кратко и по существу."
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
        
        ai_response = await openai_client.chat(messages)
        
        return {
            "text": ai_response or "Извините, не удалось обработать ваш запрос.",
            "sources": []
        }
    
    def _format_recipe_response(self, rag_result: Dict, mode: str) -> str:
        """Форматирование ответа с рецептом"""
        
        documents = rag_result["documents"]
        sources = rag_result.get("sources", [])
        
        # Объединяем найденную информацию
        combined_text = "\n\n".join(documents)
        
        # Формируем структурированный ответ
        response = f"🍹 <b>Рецепт найден в базе знаний:</b>\n\n{combined_text}"
        
        # Добавляем источники
        if sources and mode == "подробно":
            sources_text = ", ".join([s.get("chunk_id", "неизвестно") for s in sources[:3]])
            response += f"\n\n<i>Источники: {sources_text}</i>"
        
        return response
    
    def _format_knowledge_response(self, rag_result: Dict, mode: str) -> str:
        """Форматирование ответа из базы знаний"""
        
        documents = rag_result["documents"]
        sources = rag_result.get("sources", [])
        
        if len(documents) == 1:
            # Для одного документа - более лаконичный формат
            response = f"📚 <b>Информация из базы знаний:</b>\n\n{documents[0]}"
        else:
            # Для нескольких документов - объединяем
            combined_text = "\n\n".join(documents)
            response = f"📚 <b>Информация из базы знаний:</b>\n\n{combined_text}"
        
        # Добавляем источники только в подробном режиме
        if sources and mode == "подробно":
            sources_text = ", ".join([s.get("chunk_id", "неизвестно") for s in sources[:3]])
            response += f"\n\n<i>Источники: {sources_text}</i>"
        
        return response
    
    def _prepare_tts_text(self, html_text: str) -> str:
        """Подготовка текста для TTS (удаление HTML тегов)"""
        import re
        
        # Удаляем HTML теги
        clean_text = re.sub(r'<[^>]+>', '', html_text)
        
        # Удаляем эмодзи для лучшего произношения
        clean_text = re.sub(r'[^\w\s\.,!?;:-]', '', clean_text)
        
        # Ограничиваем длину для TTS
        if len(clean_text) > 500:
            clean_text = clean_text[:500] + "..."
        
        return clean_text.strip()


# Глобальный экземпляр роутера
request_router = RequestRouter()


async def process_text_request(text: str, user_id: int, mode: str = "подробно") -> Dict[str, Any]:
    """Функция-обертка для обработки текстовых запросов"""
    return await request_router.process_request(text, user_id, mode)