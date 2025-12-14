#!/usr/bin/env python3
"""
Сброс webhook для Telegram бота
"""

import asyncio
import aiohttp
from config import settings

async def reset_webhook():
    """Сбрасываем webhook и переключаемся на polling"""
    
    token = settings.telegram_bot_token
    url = f"https://api.telegram.org/bot{token}/deleteWebhook"
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url) as response:
            result = await response.json()
            print(f"Webhook reset result: {result}")
    
    # Также проверим статус
    info_url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
    async with aiohttp.ClientSession() as session:
        async with session.get(info_url) as response:
            result = await response.json()
            print(f"Webhook info: {result}")

if __name__ == "__main__":
    asyncio.run(reset_webhook())