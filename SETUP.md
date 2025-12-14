# Инструкция по настройке и запуску

## 1. Создание виртуального окружения

### Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

### Linux/Mac:
```bash
python -m venv venv
source venv/bin/activate
```

## 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

## 3. Настройка переменных окружения

Скопируйте `.env.example` в `.env` и заполните реальные значения:

```bash
cp .env.example .env
```

Отредактируйте `.env` файл:

```env
# Telegram Bot Token (получить у @BotFather)
TELEGRAM_BOT_TOKEN=your_real_telegram_bot_token

# OpenAI API Key (для GPT, Whisper, TTS, Vision)
OPENAI_API_KEY=your_real_openai_api_key

# OpenRouter API Key (для генерации изображений)
OPENROUTER_API_KEY=your_real_openrouter_api_key
```

## 4. Подготовка базы знаний

1. Поместите ваши TXT файлы в папку `data/documents/`
2. Файлы могут быть в двух форматах:

### Формат с чанками (рекомендуемый):
```
[CHUNK]
id: COCKTAIL_001_NEGRONI
tags: коктейли, классические
keywords: негрони, кампари, джин
text: Негрони - классический коктейль...

[CHUNK]
id: COCKTAIL_002_MARTINI
tags: коктейли, джин
keywords: мартини, джин, вермут
text: Мартини - король коктейлей...
```

### Обычный текстовый формат:
Файлы без разметки будут автоматически разбиты на параграфы.

## 5. Построение индекса

Запустите индексацию документов:

```bash
python -c "import asyncio; from rag.index import document_indexer; print(asyncio.run(document_indexer.build_index()))"
```

## 6. Запуск бота

```bash
python main.py
```

## 7. Команды бота

После запуска бот будет отвечать на команды:

- `/start` - описание возможностей
- `/help` - примеры вопросов
- `/reindex` - переиндексация базы знаний
- `/stats` - статистика
- `/voice on|off` - включить/выключить озвучку

## 8. Тестирование

Запуск тестов:

```bash
pytest tests/ -v
```

## 9. Примеры использования

### Текстовые запросы:
- "Рецепт Негрони"
- "Как приготовить Мохито?"
- "Чем отличается IPA от лагера?"

### Голосовые сообщения:
Отправьте голосовое сообщение с вопросом

### Генерация изображений:
- "Покажи Негрони"
- "Сгенерируй картинку Мартини"

### Анализ изображений:
Отправьте фото коктейля для анализа

## Примечания

- Текущая версия использует упрощенную RAG систему без ChromaDB для совместимости
- Для полноценной векторной базы данных установите ChromaDB отдельно
- Убедитесь что у вас есть доступ к интернету для API запросов