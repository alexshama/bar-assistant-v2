"""
Поиск по базе знаний RAG (упрощенная версия)
"""

import logging
import json
import os
from typing import List, Dict, Any, Optional

from services.openai_client import openai_client
from config import settings

logger = logging.getLogger(__name__)


class KnowledgeBaseQuery:
    """Класс для поиска по базе знаний (упрощенная версия)"""
    
    def __init__(self):
        self.index_path = os.path.join(settings.chroma_db_path, "simple_index.json")
        self.documents = []
    
    def _load_documents(self):
        """Загрузка документов из индекса"""
        
        try:
            if os.path.exists(self.index_path):
                with open(self.index_path, 'r', encoding='utf-8') as f:
                    self.documents = json.load(f)
            else:
                logger.warning(f"Индекс не найден: {self.index_path}")
                self.documents = []
                
        except Exception as e:
            logger.error(f"Ошибка при загрузке индекса: {e}")
            self.documents = []
    
    async def search(
        self, 
        query: str, 
        top_k: int = None,
        score_threshold: float = None
    ) -> Optional[Dict[str, Any]]:
        """Поиск по запросу (упрощенная версия с текстовым поиском)"""
        
        try:
            top_k = top_k or settings.rag_top_k
            
            self._load_documents()
            
            if not self.documents:
                logger.info("Документы не найдены в индексе")
                return {
                    "documents": [],
                    "sources": [],
                    "query": query
                }
            
            # Простой текстовый поиск по ключевым словам
            query_lower = query.lower()
            scored_results = []
            
            for doc in self.documents:
                score = self._calculate_text_score(query_lower, doc)
                
                if score > 0:
                    scored_results.append({
                        "document": doc['text'],
                        "metadata": doc,
                        "score": score
                    })
            
            # Сортируем по релевантности
            scored_results.sort(key=lambda x: x['score'], reverse=True)
            
            # Ограничиваем количество результатов
            scored_results = scored_results[:top_k]
            
            if not scored_results:
                logger.info("Релевантные документы не найдены")
                return {
                    "documents": [],
                    "sources": [],
                    "query": query
                }
            
            # Формируем ответ
            response_documents = [result['document'] for result in scored_results]
            response_sources = [
                {
                    "chunk_id": result['metadata'].get('chunk_id', 'unknown'),
                    "source_file": result['metadata'].get('source_file', 'unknown'),
                    "tags": result['metadata'].get('tags', []),
                    "keywords": result['metadata'].get('keywords', []),
                    "score": result['score'],
                    "distance": 1 - result['score']  # Имитируем distance
                }
                for result in scored_results
            ]
            
            logger.info(f"Найдено {len(response_documents)} релевантных документов")
            
            return {
                "documents": response_documents,
                "sources": response_sources,
                "query": query
            }
            
        except Exception as e:
            logger.error(f"Ошибка при поиске: {e}")
            return None
    
    def _calculate_text_score(self, query: str, document: Dict[str, Any]) -> float:
        """Вычисление релевантности документа к запросу"""
        
        score = 0.0
        
        # Поиск в тексте документа
        text_lower = document['text'].lower()
        chunk_id_lower = document.get('chunk_id', '').lower()
        
        # Обрабатываем склонения в запросе
        query_normalized = self._normalize_query(query)
        
        # Разбиваем запрос на слова
        query_words = query_normalized.split()
        query_lower = query_normalized.lower()
        
        # Специальная обработка для точных названий напитков
        exact_matches = {
            # Коктейли
            'b 52': 'b-52',
            'б 52': 'b-52', 
            'негрони': 'negroni',
            'мартини': 'martini',
            'мохито': 'mojito',
            'маргарита': 'margarita',
            'годфазер': 'godfather',
            'манхэттен': 'manhattan',
            'космополитен': 'cosmopolitan',
            'дайкири': 'daiquiri',
            'сингапур слинг': 'singapore_sling',
            # Спиртные напитки
            'виски': 'whisky',
            'whisky': 'whisky',
            'whiskey': 'whisky',
            'водка': 'vodka',
            'джин': 'gin',
            'ром': 'rum',
            'коньяк': 'cognac',
            'бренди': 'brandy',
            # Пиво
            'пилснер': 'pilsner',
            'лагер': 'lager',
            'эль': 'ale'
        }
        
        # Проверяем точные совпадения названий напитков
        for query_name, standard_name in exact_matches.items():
            if query_name in query_lower:
                # Ищем в ID чанка
                if standard_name in chunk_id_lower:
                    score += 10.0  # Очень высокий приоритет для точного совпадения в ID
                
                # Ищем в ключевых словах
                for keyword in document.get('keywords', []):
                    if standard_name in keyword.lower() or query_name in keyword.lower():
                        score += 5.0
                
                # Ищем в тексте (для определений типа "что такое виски")
                if standard_name in text_lower:
                    score += 3.0
        
        # Обычный поиск по словам
        for word in query_words:
            if len(word) < 2:  # Пропускаем очень короткие слова
                continue
                
            word_lower = word.lower()
            
            # Точное совпадение в ID чанка (высокий приоритет)
            if word_lower in chunk_id_lower:
                score += 3.0
            
            # Точное совпадение в тексте
            if word_lower in text_lower:
                score += 1.0
            
            # Совпадение в ключевых словах (больший вес)
            for keyword in document.get('keywords', []):
                if word_lower in keyword.lower():
                    score += 2.0
            
            # Совпадение в тегах
            for tag in document.get('tags', []):
                if word_lower in tag.lower():
                    score += 1.5
        
        # Специальная обработка для вопросов "что такое"
        if any(phrase in query_lower for phrase in ['что такое', 'что это', 'определение']):
            # Приоритет определениям (DEF в ID)
            if '_DEF_' in chunk_id_lower:
                score += 15.0  # Очень высокий приоритет для определений
            
            # Приоритет тегам basics, definition
            if 'basics' in document.get('tags', []) or 'definition' in document.get('tags', []):
                score += 10.0
            
            # Снижаем приоритет коктейлям при вопросах "что такое"
            if 'cocktail' in document.get('tags', []):
                score -= 5.0
        
        # Бонус за тип коктейля в тегах (только для рецептов)
        elif 'cocktail' in document.get('tags', []) and any(word in query_lower for word in ['коктейль', 'рецепт', 'покажи', 'сделать']):
            score += 1.0
        
        return score
    
    def _normalize_query(self, query: str) -> str:
        """Нормализация запроса - приведение склонений к базовой форме и извлечение ключевых слов"""
        
        query_lower = query.lower().strip()
        
        # Убираем знаки препинания
        import re
        query_lower = re.sub(r'[^\w\s-]', '', query_lower)
        
        # Заменяем дефисы на пробелы для составных названий
        query_lower = query_lower.replace('-', ' ')
        
        # Словарь склонений для коктейлей
        cocktail_forms = {
            'маргариты': 'маргарита',
            'негрони': 'негрони', 
            'мартини': 'мартини',
            'мохито': 'мохито',
            'дайкири': 'дайкири',
            'манхэттена': 'манхэттен',
            'космополитена': 'космополитен',
            'годфазера': 'годфазер',
            'годфазер': 'годфазер',
            'сингапур слинг': 'сингапур слинг',
            'б 52': 'b 52',
            'б52': 'b 52'
        }
        
        # Заменяем склонения на базовые формы
        for declined_form, base_form in cocktail_forms.items():
            if declined_form in query_lower:
                query_lower = query_lower.replace(declined_form, base_form)
        
        # Убираем служебные слова для лучшего поиска
        stop_words = ['как', 'сделать', 'приготовить', 'что', 'такое', 'это', 'покажи', 'фото', 'изображение', 'мне', 'рецепт']
        
        # Если это запрос с служебными словами, извлекаем только ключевые
        if any(word in query_lower for word in ['как сделать', 'как приготовить', 'покажи', 'рецепт']):
            words = query_lower.split()
            filtered_words = []
            for word in words:
                if word not in stop_words and len(word) > 1:
                    filtered_words.append(word)
            
            if filtered_words:
                # Возвращаем только ключевые слова без служебных
                return ' '.join(filtered_words)
        
        return query_lower
    
    async def search_by_tags(self, tags: List[str], top_k: int = None) -> Optional[Dict[str, Any]]:
        """Поиск по тегам"""
        
        try:
            top_k = top_k or settings.rag_top_k
            self._load_documents()
            
            if not self.documents:
                return {
                    "documents": [],
                    "sources": [],
                    "query": f"tags: {', '.join(tags)}"
                }
            
            # Ищем документы с совпадающими тегами
            matching_docs = []
            
            for doc in self.documents:
                doc_tags = [tag.lower() for tag in doc.get('tags', [])]
                
                # Проверяем пересечение тегов
                for tag in tags:
                    if tag.lower() in doc_tags:
                        matching_docs.append({
                            "document": doc['text'],
                            "metadata": doc,
                            "score": 1.0
                        })
                        break  # Достаточно одного совпадения
            
            # Ограничиваем количество результатов
            matching_docs = matching_docs[:top_k]
            
            response_documents = [result['document'] for result in matching_docs]
            response_sources = [
                {
                    "chunk_id": result['metadata'].get('chunk_id', 'unknown'),
                    "source_file": result['metadata'].get('source_file', 'unknown'),
                    "tags": result['metadata'].get('tags', []),
                    "keywords": result['metadata'].get('keywords', []),
                    "score": result['score'],
                    "distance": 0.0
                }
                for result in matching_docs
            ]
            
            return {
                "documents": response_documents,
                "sources": response_sources,
                "query": f"tags: {', '.join(tags)}"
            }
            
        except Exception as e:
            logger.error(f"Ошибка при поиске по тегам: {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики базы знаний"""
        
        try:
            self._load_documents()
            
            if not self.documents:
                return {
                    "total_documents": 0,
                    "source_files": [],
                    "tags": [],
                    "index_path": self.index_path
                }
            
            source_files = set()
            all_tags = set()
            
            for doc in self.documents:
                if doc.get('source_file'):
                    source_files.add(doc['source_file'])
                
                for tag in doc.get('tags', []):
                    all_tags.add(tag)
            
            return {
                "total_documents": len(self.documents),
                "source_files": list(source_files),
                "tags": list(all_tags),
                "index_path": self.index_path
            }
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            return {"error": str(e)}


# Глобальный экземпляр для поиска
knowledge_query = KnowledgeBaseQuery()


async def query_knowledge_base(
    query: str, 
    top_k: int = None,
    score_threshold: float = None
) -> Optional[Dict[str, Any]]:
    """Функция-обертка для поиска по базе знаний"""
    return await knowledge_query.search(query, top_k, score_threshold)


async def search_by_tags(tags: List[str], top_k: int = None) -> Optional[Dict[str, Any]]:
    """Функция-обертка для поиска по тегам"""
    return await knowledge_query.search_by_tags(tags, top_k)


def get_knowledge_stats() -> Dict[str, Any]:
    """Функция-обертка для получения статистики"""
    return knowledge_query.get_stats()