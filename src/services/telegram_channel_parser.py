"""
Парсер для Telegram-каналов с использованием Telethon.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from telethon import TelegramClient
from telethon.tl.types import Message
from telethon.errors import FloodWaitError, ChannelPrivateError, ChatAdminRequiredError

from src.config.telegram_config import TelegramConfig
from src.models.database import News, Source
from src.services.postgresql_database_service import PostgreSQLDatabaseService

logger = logging.getLogger(__name__)

class TelegramChannelParser:
    """Парсер для Telegram-каналов."""
    
    def __init__(self):
        """Инициализация парсера."""
        self.client = None
        self.db_service = PostgreSQLDatabaseService()
        
        # Проверяем конфигурацию
        if not TelegramConfig.validate_config():
            raise ValueError("Некорректная конфигурация Telegram API")
        
        logger.info("✅ TelegramChannelParser инициализирован")
    
    async def __aenter__(self):
        """Асинхронный контекстный менеджер - вход."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер - выход."""
        await self.disconnect()
    
    async def connect(self):
        """Подключение к Telegram API."""
        try:
            self.client = TelegramClient(
                'ai_news_session',
                TelegramConfig.API_ID,
                TelegramConfig.API_HASH
            )
            
            await self.client.start()
            logger.info("✅ Подключение к Telegram API установлено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Telegram API: {e}")
            raise
    
    async def disconnect(self):
        """Отключение от Telegram API."""
        if self.client:
            await self.client.disconnect()
            logger.info("🔌 Отключение от Telegram API")
    
    async def parse_channel(self, channel_username: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Парсинг конкретного канала.
        
        Args:
            channel_username: Username канала (без @)
            limit: Максимум сообщений для парсинга
            
        Returns:
            Список новостей из канала
        """
        try:
            logger.info(f"🔍 Парсинг канала @{channel_username}")
            
            # Получаем канал
            channel = await self.client.get_entity(f"@{channel_username}")
            if not channel:
                logger.error(f"❌ Канал @{channel_username} не найден")
                return []
            
            # Получаем сообщения
            messages = await self.client.get_messages(channel, limit=limit)
            logger.info(f"📱 Получено {len(messages)} сообщений из @{channel_username}")
            
            # Извлекаем новости из сообщений
            news_list = []
            for message in messages:
                if message and message.text:
                    news = await self._extract_news_from_message(message, channel_username)
                    if news:
                        news_list.append(news)
            
            logger.info(f"📰 Извлечено {len(news_list)} новостей из @{channel_username}")
            return news_list
            
        except ChannelPrivateError:
            logger.error(f"❌ Канал @{channel_username} приватный")
            return []
        except ChatAdminRequiredError:
            logger.error(f"❌ Нет доступа к каналу @{channel_username}")
            return []
        except FloodWaitError as e:
            logger.warning(f"⚠️ Превышен лимит запросов к @{channel_username}, ждем {e.seconds} секунд")
            await asyncio.sleep(e.seconds)
            return []
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга канала @{channel_username}: {e}")
            return []
    
    async def _extract_news_from_message(self, message: Message, channel_username: str) -> Optional[Dict[str, Any]]:
        """
        Извлекает новость из сообщения Telegram.
        
        Args:
            message: Сообщение Telegram
            channel_username: Username канала
            
        Returns:
            Словарь с данными новости или None
        """
        try:
            # Проверяем, что сообщение содержит текст
            if not message.text or len(message.text.strip()) < 20:
                return None
            
            # ПРОВЕРЯЕМ ВРЕМЯ: берем только новости за последние 24 часа
            message_time = message.date
            current_time = datetime.utcnow()
            
            # Приводим оба времени к offset-naive для корректного сравнения
            if message_time.tzinfo is not None:
                message_time = message_time.replace(tzinfo=None)
            if current_time.tzinfo is not None:
                current_time = current_time.replace(tzinfo=None)
            
            time_difference = current_time - message_time
            
            # Если сообщение старше 24 часов - пропускаем
            if time_difference.total_seconds() > 24 * 60 * 60:  # 24 часа в секундах
                logger.debug(f"⏰ Пропускаем старое сообщение: {message_time} (разница: {time_difference})")
                return None
            
            # Извлекаем заголовок (первые 100 символов)
            title = message.text[:100].strip()
            if title.endswith('...'):
                title = title[:-3]
            
            # Получаем полный текст
            content = message.text.strip()
            
            # Создаем URL на сообщение
            source_url = f"https://t.me/{channel_username}/{message.id}"
            
            # Формируем новость
            news_data = {
                'title': title,
                'content': content,
                'source_channel_username': channel_username,
                'source_message_id': message.id,
                'source_url': source_url,
                'raw_content': message.text,
                'published_at': message.date,
                'created_at': datetime.utcnow(),
                'status': 'new'
            }
            
            return news_data
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения новости из сообщения: {e}")
            return None