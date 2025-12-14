# 🍹 Telegram Bot "Барный ассистент"

Интеллектуальный Telegram бот для консультаций по алкогольным напиткам и коктейлям с поддержкой RAG (Retrieval-Augmented Generation), генерации изображений и голосового взаимодействия.

## ✨ Возможности

### 🔍 Поиск и консультации
- **Рецепты коктейлей** - более 100 коктейлей в базе знаний
- **Информация о напитках** - виски, джин, ром, пиво и другие
- **Умные рекомендации** - советы по выбору и замене напитков
- **Обработка склонений** - понимает "маргариты", "годфазера" и т.д.

### 🖼 Генерация изображений
- **AI-генерация коктейлей** - через Gemini 2.5 Flash Image Preview
- **Правильные цвета** - автоматическое определение цвета по ингредиентам
- **Кэширование изображений** - экономия API вызовов
- **Специальные промпты** - для сложных коктейлей (B-52, слоистые)

### 🎤 Голосовое взаимодействие
- **Speech-to-Text** - распознавание голосовых сообщений
- **Text-to-Speech** - голосовые ответы
- **Fallback система** - OpenAI + OpenRouter для надежности

### 🧠 RAG система
- **Векторный поиск** - по базе знаний из 200+ чанков
- **Умная маршрутизация** - автоматическое определение типа запроса
- **Контекстные ответы** - на основе специализированных данных

## 🚀 Технологии

- **Python 3.8+**
- **aiogram 3.x** - Telegram Bot API
- **OpenAI API** - GPT-4, Whisper, TTS
- **OpenRouter** - Gemini 2.5 Flash для изображений
- **JSON-based RAG** - упрощенная векторная база данных
- **aiohttp** - асинхронные HTTP запросы

## 📦 Установка

1. **Клонируйте репозиторий:**
```bash
git clone https://github.com/yourusername/telegram-bar-assistant.git
cd telegram-bar-assistant
```

2. **Создайте виртуальное окружение:**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

4. **Настройте переменные окружения:**
```bash
cp .env.example .env
```

Отредактируйте `.env` файл:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=your_openai_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_IMAGE_MODEL=google/gemini-2.5-flash-image-preview
```

5. **Запустите бота:**
```bash
python main.py
```

## ⚙️ Конфигурация

### API ключи
- **Telegram Bot Token** - получите у [@BotFather](https://t.me/botfather)
- **OpenAI API Key** - для GPT-4, Whisper, TTS
- **OpenRouter API Key** - для Gemini генерации изображений

### Настройки бота
- Режимы ответов: подробно/кратко
- Кэширование изображений
- Административные команды

## 📁 Структура проекта

```
telegram-bar-assistant/
├── 📄 main.py                 # Точка входа
├── 🤖 bot.py                  # Создание и настройка бота
├── ⚙️ config.py               # Конфигурация и настройки
├── 📁 handlers/               # Обработчики сообщений
│   ├── start.py              # Команды /start, /help
│   ├── text.py               # Текстовые сообщения
│   ├── voice.py              # Голосовые сообщения
│   ├── image.py              # Изображения
│   └── admin.py              # Административные команды
├── 📁 services/               # Сервисы и API клиенты
│   ├── router.py             # Маршрутизация запросов
│   ├── openai_client.py      # OpenAI API (GPT, Whisper, TTS)
│   ├── openrouter_client.py  # OpenRouter API (Gemini)
│   ├── image_cache.py        # Кэширование изображений
│   ├── stt.py                # Speech-to-Text
│   └── tts.py                # Text-to-Speech
├── 📁 rag/                    # RAG система
│   ├── loader.py             # Загрузка данных
│   ├── index.py              # Индексирование
│   └── query.py              # Поиск и запросы
├── 📁 data/                   # Данные и кэш
│   ├── documents/            # База знаний (TXT файлы)
│   ├── chroma_db/           # Индексы RAG
│   └── images/              # Кэш изображений
└── 📄 requirements.txt        # Python зависимости
```

## 🎯 Использование

### Примеры запросов

**Рецепты коктейлей:**
- "Рецепт Негрони"
- "Как приготовить Мохито?"
- "Покажи фото Маргариты"

**Информация о напитках:**
- "Что такое виски?"
- "Чем отличается IPA от лагера?"

**Рекомендации:**
- "Какой виски лучше предложить вместо бурбона?"
- "Посоветуй коктейль с джином"

**Голосовые команды:**
- Отправьте голосовое сообщение с любым вопросом

### Административные команды
- `/cache_stats` - статистика кэша изображений
- `/clear_cache` - очистка кэша (только админ)

## 🔧 Разработка

### Добавление новых коктейлей
1. Добавьте данные в `data/documents/`
2. Перезапустите бота для переиндексации

### Настройка промптов
- Редактируйте `services/router.py` для изменения промптов генерации изображений
- Специальные промпты для сложных коктейлей в `_create_cocktail_image_prompt()`

### Логирование
Все компоненты используют Python logging:
```python
import logging
logger = logging.getLogger(__name__)
```

## 🤝 Вклад в проект

1. Fork репозиторий
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📝 Лицензия

Этот проект лицензирован под MIT License - см. файл [LICENSE](LICENSE) для деталей.

## 🙏 Благодарности

- [OpenAI](https://openai.com/) за GPT-4, Whisper и TTS API
- [OpenRouter](https://openrouter.ai/) за доступ к Gemini модели
- [aiogram](https://aiogram.dev/) за отличную библиотеку для Telegram ботов

## 📞 Поддержка

Если у вас есть вопросы или проблемы:
1. Проверьте [Issues](https://github.com/yourusername/telegram-bar-assistant/issues)
2. Создайте новый Issue с подробным описанием
3. Приложите логи и конфигурацию (без API ключей!)

---

**Сделано с ❤️ для любителей качественных коктейлей**