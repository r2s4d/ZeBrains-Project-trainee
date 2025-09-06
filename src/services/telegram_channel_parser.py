"""
Парсер для Telegram-каналов с использованием Telethon.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from telethon import TelegramClient
from telethon.tl.types import Message, Channel
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
    
    async def parse_all_channels(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Парсинг всех активных каналов.
        
        Returns:
            Словарь с новостями по каналам
        """
        try:
            logger.info("🚀 Начинаем парсинг всех каналов")
            
            all_news = {}
            active_channels = TelegramConfig.get_active_channels()
            
            for channel in active_channels:
                username = channel['username']
                logger.info(f"📱 Парсинг канала @{username}")
                
                # Парсим канал
                channel_news = await self.parse_channel(username)
                all_news[username] = channel_news
                
                # Пауза между каналами (избегаем rate limiting)
                await asyncio.sleep(2)
            
            total_news = sum(len(news) for news in all_news.values())
            logger.info(f"✅ Парсинг завершен. Всего новостей: {total_news}")
            
            return all_news
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга всех каналов: {e}")
            return {}
    
    async def save_news_to_database(self, news_list: List[Dict[str, Any]]) -> int:
        """
        Сохраняет новости в базу данных.
        
        Args:
            news_list: Список новостей для сохранения
            
        Returns:
            Количество сохраненных новостей
        """
        try:
            if not news_list:
                return 0
            
            saved_count = 0
            session = self.db_service.get_session()
            
            if not session:
                logger.error("❌ Не удалось получить сессию базы данных")
                return 0
            
            try:
                for news_data in news_list:
                    # Проверяем, не дубликат ли это
                    existing_news = session.query(News).filter_by(
                        source_message_id=news_data['source_message_id'],
                        source_channel_username=news_data['source_channel_username']
                    ).first()
                    
                    if existing_news:
                        logger.debug(f"⚠️ Новость уже существует: {news_data['title'][:50]}...")
                        continue
                    
                    # Создаем новую новость
                    news = News(
                        title=news_data['title'],
                        content=news_data['content'],
                        source_channel_username=news_data['source_channel_username'],
                        source_message_id=news_data['source_message_id'],
                        source_url=news_data['source_url'],
                        raw_content=news_data['raw_content'],
                        published_at=news_data['published_at'],
                        created_at=news_data['created_at'],
                        status=news_data['status']
                    )
                    
                    session.add(news)
                    saved_count += 1
                
                session.commit()
                logger.info(f"✅ Сохранено {saved_count} новых новостей в базу данных")
                
            finally:
                session.close()
            
            return saved_count
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения новостей в базу данных: {e}")
            return 0
    
    async def get_parsing_statistics(self) -> Dict[str, Any]:
        """
        Получает статистику парсинга.
        
        Returns:
            Словарь со статистикой
        """
        try:
            session = self.db_service.get_session()
            if not session:
                return {}
            
            try:
                # Общее количество новостей
                total_news = session.query(News).count()
                
                # Новости по каналам
                news_by_channel = {}
                for channel in TelegramConfig.get_active_channels():
                    username = channel['username']
                    count = session.query(News).filter_by(source_channel_username=username).count()
                    news_by_channel[username] = count
                
                # Новости за последние 24 часа
                yesterday = datetime.utcnow() - timedelta(days=1)
                recent_news = session.query(News).filter(
                    News.created_at >= yesterday
                ).count()
                
                stats = {
                    'total_news': total_news,
                    'recent_news_24h': recent_news,
                    'news_by_channel': news_by_channel,
                    'last_update': datetime.utcnow().isoformat()
                }
                
                return stats
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики парсинга: {e}")
            return {}

# Тестирование парсера
async def test_parser():
    """Тестирование парсера на одном канале."""
    try:
        async with TelegramChannelParser() as parser:
            # Тестируем на канале ai_ins
            news = await parser.parse_channel('ai_ins', limit=5)
            print(f"📰 Получено {len(news)} новостей из @ai_ins")
            
            for i, item in enumerate(news[:3], 1):
                print(f"\n{i}. {item['title']}")
                print(f"   Канал: @{item['source_channel_username']}")
                print(f"   URL: {item['source_url']}")
                print(f"   Длина: {len(item['content'])} символов")
            
            # Получаем статистику
            stats = await parser.get_parsing_statistics()
            print(f"\n📊 Статистика: {stats}")
            
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")

if __name__ == "__main__":
    # Запускаем тест
    asyncio.run(test_parser())
