"""
Загрузчик документов для RAG системы
"""

import os
import logging
from typing import List, Dict, Any
from config import settings

logger = logging.getLogger(__name__)


class DocumentLoader:
    """Загрузчик документов из TXT файлов"""
    
    def __init__(self, documents_path: str = None):
        self.documents_path = documents_path or settings.documents_path
    
    def load_documents(self) -> List[Dict[str, Any]]:
        """Загрузка всех документов из папки"""
        
        documents = []
        
        if not os.path.exists(self.documents_path):
            logger.warning(f"Папка с документами не найдена: {self.documents_path}")
            return documents
        
        # Проходим по всем TXT файлам
        for filename in os.listdir(self.documents_path):
            if filename.endswith('.txt'):
                file_path = os.path.join(self.documents_path, filename)
                
                try:
                    file_documents = self._load_file(file_path, filename)
                    documents.extend(file_documents)
                    logger.info(f"Загружен файл {filename}: {len(file_documents)} чанков")
                    
                except Exception as e:
                    logger.error(f"Ошибка при загрузке файла {filename}: {e}")
        
        logger.info(f"Всего загружено документов: {len(documents)}")
        return documents
    
    def _load_file(self, file_path: str, filename: str) -> List[Dict[str, Any]]:
        """Загрузка одного файла"""
        
        documents = []
        
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Проверяем формат файла
        if '[CHUNK]' in content:
            # Файл в формате чанков
            documents = self._parse_chunked_format(content, filename)
        else:
            # Обычный текстовый файл - разбиваем на чанки
            documents = self._parse_plain_text(content, filename)
        
        return documents
    
    def _parse_chunked_format(self, content: str, filename: str) -> List[Dict[str, Any]]:
        """Парсинг файла в формате чанков"""
        
        documents = []
        chunks = content.split('[CHUNK]')[1:]  # Убираем первый пустой элемент
        
        for i, chunk in enumerate(chunks):
            try:
                doc = self._parse_chunk(chunk.strip(), filename, i)
                if doc:
                    documents.append(doc)
            except Exception as e:
                logger.error(f"Ошибка при парсинге чанка {i} в файле {filename}: {e}")
        
        return documents
    
    def _parse_chunk(self, chunk_text: str, filename: str, chunk_index: int) -> Dict[str, Any]:
        """Парсинг отдельного чанка"""
        
        lines = chunk_text.split('\n')
        
        chunk_data = {
            'chunk_id': f"{filename}_{chunk_index}",
            'tags': [],
            'keywords': [],
            'text': '',
            'source_file': filename
        }
        
        text_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('id:'):
                chunk_data['chunk_id'] = line[3:].strip()
            elif line.startswith('tags:'):
                tags_str = line[5:].strip()
                chunk_data['tags'] = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
            elif line.startswith('keywords:'):
                keywords_str = line[9:].strip()
                chunk_data['keywords'] = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
            elif line.startswith('text:'):
                text_lines.append(line[5:].strip())
            else:
                # Продолжение текста
                text_lines.append(line)
        
        chunk_data['text'] = '\n'.join(text_lines).strip()
        
        # Проверяем что есть текст
        if not chunk_data['text']:
            logger.warning(f"Пустой текст в чанке {chunk_data['chunk_id']}")
            return None
        
        return chunk_data
    
    def _parse_plain_text(self, content: str, filename: str) -> List[Dict[str, Any]]:
        """Парсинг обычного текстового файла"""
        
        documents = []
        
        # Разбиваем на параграфы
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        for i, paragraph in enumerate(paragraphs):
            if len(paragraph) < 50:  # Пропускаем слишком короткие параграфы
                continue
            
            chunk_data = {
                'chunk_id': f"{filename}_paragraph_{i}",
                'tags': [self._extract_category_from_filename(filename)],
                'keywords': self._extract_keywords_from_text(paragraph),
                'text': paragraph,
                'source_file': filename
            }
            
            documents.append(chunk_data)
        
        return documents
    
    def _extract_category_from_filename(self, filename: str) -> str:
        """Извлечение категории из имени файла"""
        
        filename_lower = filename.lower()
        
        if 'cocktail' in filename_lower or 'коктейль' in filename_lower:
            return 'коктейли'
        elif 'beer' in filename_lower or 'пиво' in filename_lower:
            return 'пиво'
        elif 'whisky' in filename_lower or 'whiskey' in filename_lower or 'виски' in filename_lower:
            return 'виски'
        elif 'vodka' in filename_lower or 'водка' in filename_lower:
            return 'водка'
        elif 'gin' in filename_lower or 'джин' in filename_lower:
            return 'джин'
        elif 'rum' in filename_lower or 'ром' in filename_lower:
            return 'ром'
        elif 'wine' in filename_lower or 'вино' in filename_lower:
            return 'вино'
        else:
            return 'общее'
    
    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """Простое извлечение ключевых слов из текста"""
        
        # Список ключевых слов для барной тематики
        bar_keywords = [
            'коктейль', 'напиток', 'алкоголь', 'пиво', 'виски', 'водка', 'джин', 'ром', 
            'текила', 'вино', 'шампанское', 'ликер', 'сироп', 'биттер', 'лед', 'гарнир',
            'бокал', 'стакан', 'шейкер', 'стрейнер', 'бар', 'бармен', 'рецепт', 'мл',
            'унция', 'dash', 'splash', 'мудлинг', 'стир', 'шейк', 'билд'
        ]
        
        text_lower = text.lower()
        found_keywords = []
        
        for keyword in bar_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords[:10]  # Ограничиваем количество ключевых слов


# Глобальный экземпляр загрузчика
document_loader = DocumentLoader()