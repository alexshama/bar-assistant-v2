# Deploy Guide

## 1. Подготовка сервера

Рекомендуемый минимум:

- Ubuntu 22.04+ или другой Linux с `systemd`
- Python 3.10+
- 1 vCPU / 1 GB RAM

Установите базовые пакеты:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
```

Если хотите более надежную аудио-конвертацию через `pydub`, дополнительно:

```bash
sudo apt install -y ffmpeg
```

## 2. Копирование проекта

```bash
git clone <your-repository-url> bar-assist
cd bar-assist
```

Если деплой без git:

- загрузите архив проекта на сервер;
- распакуйте в рабочую директорию;
- перейдите в каталог проекта.

## 3. Виртуальное окружение и зависимости

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Настройка окружения

```bash
cp .env.example .env
```

Минимально заполните:

```env
TELEGRAM_BOT_TOKEN=...
OPENAI_API_KEY=...
OPENROUTER_API_KEY=...
ADMIN_USER_IDS=123456789
LOG_LEVEL=INFO
```

## 5. Первый запуск

```bash
source venv/bin/activate
python main.py
```

Если индекс базы знаний еще не существует, приложение соберет его при старте автоматически.

## 6. Запуск как systemd service

Создайте файл `/etc/systemd/system/bar-assistant.service`:

```ini
[Unit]
Description=Bar Assistant Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/bar-assist
Environment="PYTHONUNBUFFERED=1"
ExecStart=/home/ubuntu/bar-assist/venv/bin/python /home/ubuntu/bar-assist/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Подставьте своего пользователя и путь к проекту.

Активируйте сервис:

```bash
sudo systemctl daemon-reload
sudo systemctl enable bar-assistant
sudo systemctl start bar-assistant
sudo systemctl status bar-assistant
```

Логи:

```bash
journalctl -u bar-assistant -f
```

## 7. Обновление на сервере

```bash
cd /home/ubuntu/bar-assist
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart bar-assistant
```

Если меняли документы в `data/documents/`, после обновления:

- вызовите `/reindex` в боте;
- или удалите старый индекс и перезапустите сервис.

## 8. Что проверить после деплоя

- `/start`
- `/help`
- текстовый рецепт коктейля
- запрос справки по напитку
- генерацию изображения
- голосовое сообщение
- `/cache_stats`
- `/reindex`

## 9. Production notes

- Не храните `.env` в git.
- Не запускайте бота от root.
- Если нужен один инстанс на несколько серверов, вынесите `user_settings.json` в БД или внешний storage.
- Следите за лимитами OpenAI/OpenRouter и логами `systemd`.
