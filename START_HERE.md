# 🚀 Быстрый старт "Барный ассистент"

## Шаг 1: Активация виртуального окружения

### Windows:
Дважды кликните на файл `activate.bat` или выполните в командной строке:
```cmd
venv\Scripts\activate
```

### Linux/Mac:
```bash
chmod +x activate.sh
./activate.sh
```
или
```bash
source venv/bin/activate
```

## Шаг 2: Установка зависимостей
```bash
pip install -r requirements.txt
```

## Шаг 3: Настройка API ключей

Отредактируйте файл `.env` и добавьте ваши реальные API ключи:

```env
TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather
OPENAI_API_KEY=ваш_ключ_OpenAI
OPENROUTER_API_KEY=ваш_ключ_OpenRouter
```

### Где получить ключи:
- **Telegram Bot Token**: [@BotFather](https://t.me/BotFather) в Telegram
- **OpenAI API Key**: [platform.openai.com](https://platform.openai.com/api-keys)
- **OpenRouter API Key**: [openrouter.ai](https://openrouter.ai/keys)

## Шаг 4: Добавление базы знаний

Поместите ваши TXT файлы с информацией о коктейлях, пиве и алкоголе в папку:
```
data/documents/
```

Пример уже есть в файле `cocktails_classic.txt`

## Шаг 5: Построение индекса

```bash
python -c "import asyncio; from rag.index import document_indexer; print(asyncio.run(document_indexer.build_index()))"
```

## Шаг 6: Запуск бота

```bash
python main.py
```

## ✅ Готово!

Бот запущен и готов к работе! Найдите его в Telegram и отправьте `/start`

## 🔧 Проверка работы

1. Отправьте `/start` - должно прийти приветствие
2. Спросите "рецепт негрони" - должен найти в базе знаний
3. Отправьте голосовое сообщение - должно распознать речь
4. Попросите "покажи негрони" - должно сгенерировать изображение

## 📞 Поддержка

Если что-то не работает:
1. Проверьте что все API ключи корректные
2. Убедитесь что виртуальное окружение активировано
3. Проверьте логи в консоли при запуске бота