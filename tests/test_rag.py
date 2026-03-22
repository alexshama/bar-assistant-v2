"""
Тесты для RAG системы
"""

import pytest
import asyncio
import os
import tempfile
import shutil
from unittest.mock import patch, AsyncMock

from rag.loader import DocumentLoader
from rag.index import DocumentIndexer
from rag.query import KnowledgeBaseQuery


class TestDocumentLoader:
    """Тесты загрузчика документов"""
    
    def setup_method(self):
        """Настройка для каждого теста"""
        self.temp_dir = tempfile.mkdtemp()
        self.loader = DocumentLoader(self.temp_dir)
    
    def teardown_method(self):
        """Очистка после каждого теста"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_chunked_format(self):
        """Тест загрузки файла в формате чанков"""
        
        # Создаем тестовый файл
        test_content = """
[CHUNK]
id: TEST_001_NEGRONI
tags: коктейли, тест
keywords: негрони, тест
text: Тестовый рецепт Негрони
Ингредиенты: джин, вермут, кампари

[CHUNK]
id: TEST_002_MARTINI
tags: коктейли, классика
keywords: мартини, джин
text: Тестовый рецепт Мартини
Ингредиенты: джин, вермут
        """
        
        test_file = os.path.join(self.temp_dir, "test_cocktails.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        # Загружаем документы
        documents = self.loader.load_documents()
        
        # Проверяем результат
        assert len(documents) == 2
        assert documents[0]['chunk_id'] == 'TEST_001_NEGRONI'
        assert 'коктейли' in documents[0]['tags']
        assert 'негрони' in documents[0]['keywords']
        assert 'Негрони' in documents[0]['text']
    
    def test_load_plain_text(self):
        """Тест загрузки обычного текстового файла"""
        
        test_content = """
Это первый параграф о коктейлях. Он содержит информацию о том, как готовить напитки в баре.

Это второй параграф о барном оборудовании. Здесь описываются шейкеры, стрейнеры и другие инструменты.

Короткий текст.

Это третий параграф о технике приготовления. Важно соблюдать пропорции и температуру.
        """
        
        test_file = os.path.join(self.temp_dir, "test_general.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        documents = self.loader.load_documents()
        
        # Проверяем что короткие параграфы пропускаются
        assert len(documents) == 3  # Короткий текст должен быть пропущен
        assert all(len(doc['text']) >= 50 for doc in documents)
    
    def test_extract_category_from_filename(self):
        """Тест извлечения категории из имени файла"""
        
        assert self.loader._extract_category_from_filename("cocktails_classic.txt") == "коктейли"
        assert self.loader._extract_category_from_filename("beer_styles.txt") == "пиво"
        assert self.loader._extract_category_from_filename("whisky_guide.txt") == "виски"
        assert self.loader._extract_category_from_filename("random_file.txt") == "общее"


class TestRAGIntegration:
    """Интеграционные тесты RAG системы"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Настройка для тестов"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Создаем тестовые документы
        test_content = """
[CHUNK]
id: TEST_NEGRONI_001
tags: коктейли, классические
keywords: негрони, кампари, джин, вермут
text: Негрони - классический итальянский коктейль. Состоит из равных частей джина, красного вермута и Кампари. Подается в олд фэшн стакане со льдом и долькой апельсина.

[CHUNK]
id: TEST_MARTINI_001
tags: коктейли, джин
keywords: мартини, джин, вермут, оливка
text: Мартини - элегантный коктейль из джина и сухого вермута. Подается в охлажденной коктейльной рюмке с оливкой или лимонной цедрой.
        """
        
        test_file = os.path.join(self.temp_dir, "test_cocktails.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        yield
        
        # Очистка
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('rag.index.settings')
    @patch('services.openai_client.openai_client.embeddings')
    async def test_build_and_query_index(self, mock_embeddings, mock_settings):
        """Тест построения индекса и поиска"""
        
        # Настраиваем моки
        mock_settings.chroma_db_path = os.path.join(self.temp_dir, "chroma")
        mock_settings.documents_path = self.temp_dir
        mock_settings.rag_top_k = 5
        mock_settings.rag_score_threshold = 0.7
        
        # Мокаем эмбеддинги
        mock_embeddings.return_value = [
            [0.1, 0.2, 0.3] * 100,  # Для первого документа
            [0.2, 0.3, 0.4] * 100   # Для второго документа
        ]
        
        # Создаем индексатор и строим индекс
        indexer = DocumentIndexer()
        result = await indexer.build_index()
        
        assert result['success'] == True
        assert result['chunks_count'] == 2
        
        # Тестируем поиск
        mock_embeddings.return_value = [[0.15, 0.25, 0.35] * 100]  # Запрос похожий на первый документ
        
        query_engine = KnowledgeBaseQuery()
        search_result = await query_engine.search("рецепт негрони")
        
        assert search_result is not None
        assert len(search_result['documents']) > 0
        assert 'негрони' in search_result['documents'][0].lower()


@pytest.mark.asyncio
async def test_query_knowledge_base_mock():
    """Тест функции поиска с моками"""
    
    with patch('rag.query.knowledge_query') as mock_query:
        mock_query.search = AsyncMock(return_value={
            'documents': ['Негрони - классический коктейль...'],
            'sources': [{'chunk_id': 'TEST_NEGRONI_001', 'score': 0.95}],
            'query': 'рецепт негрони'
        })
        
        from rag.query import query_knowledge_base
        
        result = await query_knowledge_base("рецепт негрони")
        
        assert result is not None
        assert len(result['documents']) == 1
        assert 'негрони' in result['documents'][0].lower()
        assert result['sources'][0]['score'] == 0.95


if __name__ == "__main__":
    pytest.main([__file__])