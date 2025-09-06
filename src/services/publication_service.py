#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PublicationService - сервис для публикации новостей в Telegram-канал

Этот сервис:
1. Публикует одобренные новости в канал
2. Создает и публикует ежедневные дайджесты
3. Управляет очередью публикаций
4. Интегрируется с существующими сервисами
"""

import asyncio
import logging
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from enum import Enum

from src.services.database_service import DatabaseService
from src.services.post_formatter_service import PostFormatterService
from src.models.database import News, Source, Expert, Comment

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PublicationStatus(Enum):
    """Статусы публикации."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"

class PublicationType(Enum):
    """Типы публикаций."""
    SINGLE_NEWS = "single_news"
    DAILY_DIGEST = "daily_digest"
    WEEKLY_DIGEST = "weekly_digest"
    EXPERT_ANALYSIS = "expert_analysis"

class PublicationService:
    """
    Сервис для публикации новостей в Telegram-канал.
    
    Основные функции:
    - Публикация отдельных новостей
    - Создание и публикация дайджестов
    - Управление очередью публикаций
    - Планирование публикаций
    """
    
    def __init__(self, database_service: DatabaseService, bot_token: str, channel_id: str):
        """
        Инициализация сервиса.
        
        Args:
            database_service: Сервис для работы с базой данных
            bot_token: Токен Telegram бота
            channel_id: ID канала для публикации (@channel_name или -1001234567890)
        """
        self.db = database_service
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.post_formatter = PostFormatterService()
        
        # Настройки публикации
        self.max_posts_per_day = 10
        self.publication_interval = 2  # часа между публикациями
        self.auto_publish_enabled = True
        
        logger.info(f"PublicationService инициализирован для канала {channel_id}")
    
    # ==================== ПУБЛИКАЦИЯ ОТДЕЛЬНЫХ НОВОСТЕЙ ====================
    
    async def publish_news(self, news_id: int) -> Dict[str, Any]:
        """
        Публикует отдельную новость в канал.
        
        Args:
            news_id: ID новости для публикации
            
        Returns:
            Dict с результатами публикации
        """
        try:
            logger.info(f"📤 Публикация новости {news_id} в канал")
            
            # Получаем новость
            news = self.db.get_news_by_id(news_id)
            if not news:
                return {
                    "success": False,
                    "error": f"Новость {news_id} не найдена"
                }
            
            # Проверяем статус новости
            if news.status != "approved":
                return {
                    "success": False,
                    "error": f"Новость {news_id} не одобрена для публикации (статус: {news.status})"
                }
            
            # Форматируем пост
            formatted_post = self.post_formatter.format_single_news(news)
            
            # Отправляем в Telegram канал
            telegram_result = await self._send_to_telegram_channel(formatted_post)
            if not telegram_result["success"]:
                logger.error(f"❌ Ошибка отправки в Telegram: {telegram_result['error']}")
                return {
                    "success": False,
                    "error": f"Ошибка отправки в канал: {telegram_result['error']}"
                }
            
            logger.info(f"✅ Новость {news_id} успешно отправлена в канал")
            logger.info(f"📝 Форматированный пост: {formatted_post[:100]}...")
            
            # Обновляем статус новости
            await self._update_news_publication_status(news_id, PublicationStatus.PUBLISHED)
            
            return {
                "success": True,
                "news_id": news_id,
                "title": news.title,
                "message": "Новость успешно опубликована в канале",
                "formatted_post": formatted_post
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка публикации новости {news_id}: {e}")
            await self._update_news_publication_status(news_id, PublicationStatus.FAILED)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def publish_news_batch(self, news_ids: List[int]) -> Dict[str, Any]:
        """
        Публикует несколько новостей в канал.
        
        Args:
            news_ids: Список ID новостей для публикации
            
        Returns:
            Dict с результатами публикации
        """
        logger.info(f"📤 Пакетная публикация {len(news_ids)} новостей в канал")
        
        results = {
            "success": 0,
            "failed": 0,
            "total": len(news_ids),
            "details": []
        }
        
        for news_id in news_ids:
            try:
                result = await self.publish_news(news_id)
                results["details"].append({
                    "news_id": news_id,
                    "result": result
                })
                
                if result["success"]:
                    results["success"] += 1
                else:
                    results["failed"] += 1
                
                # Пауза между публикациями
                await asyncio.sleep(30)  # 30 секунд между постами
                
            except Exception as e:
                logger.error(f"❌ Ошибка публикации новости {news_id}: {e}")
                results["failed"] += 1
                results["details"].append({
                    "news_id": news_id,
                    "result": {"success": False, "error": str(e)}
                })
        
        logger.info(f"✅ Пакетная публикация завершена: {results}")
        return results
    
    # ==================== ПУБЛИКАЦИЯ ДАЙДЖЕСТОВ ====================
    
    async def publish_daily_digest(self) -> Dict[str, Any]:
        """
        Создает и публикует ежедневный дайджест в канал.
        
        Returns:
            Dict с результатами публикации
        """
        try:
            logger.info("📊 Создание и публикация ежедневного дайджеста")
            
            # Получаем новости за день
            daily_news = await self._get_daily_news()
            if not daily_news:
                return {
                    "success": False,
                    "error": "Нет новостей для дайджеста"
                }
            
            # Создаем дайджест
            digest_content = self.post_formatter.format_daily_digest(daily_news)
            
            # Отправляем в Telegram канал
            telegram_result = await self._send_to_telegram_channel(digest_content)
            if not telegram_result["success"]:
                logger.error(f"❌ Ошибка отправки дайджеста в Telegram: {telegram_result['error']}")
                return {
                    "success": False,
                    "error": f"Ошибка отправки дайджеста в канал: {telegram_result['error']}"
                }
            
            logger.info("✅ Ежедневный дайджест успешно отправлен в канал")
            logger.info(f"📝 Содержимое дайджеста: {digest_content[:100]}...")
            
            return {
                "success": True,
                "type": "daily_digest",
                "news_count": len(daily_news),
                "message": "Ежедневный дайджест успешно опубликован в канале",
                "content": digest_content
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка публикации ежедневного дайджеста: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def publish_weekly_digest(self) -> Dict[str, Any]:
        """
        Создает и публикует еженедельный дайджест в канал.
        
        Returns:
            Dict с результатами публикации
        """
        try:
            logger.info("📊 Создание и публикация еженедельного дайджеста")
            
            # Получаем новости за неделю
            weekly_news = await self._get_weekly_news()
            if not weekly_news:
                return {
                    "success": False,
                    "error": "Нет новостей для еженедельного дайджеста"
                }
            
            # Создаем дайджест
            digest_content = self.post_formatter.format_weekly_digest(weekly_news)
            
            # Отправляем в Telegram канал
            telegram_result = await self._send_to_telegram_channel(digest_content)
            if not telegram_result["success"]:
                logger.error(f"❌ Ошибка отправки еженедельного дайджеста в Telegram: {telegram_result['error']}")
                return {
                    "success": False,
                    "error": f"Ошибка отправки еженедельного дайджеста в канал: {telegram_result['error']}"
                }
            
            logger.info("✅ Еженедельный дайджест успешно отправлен в канал")
            
            return {
                "success": True,
                "type": "weekly_digest",
                "news_count": len(weekly_news),
                "message": "Еженедельный дайджест успешно опубликован в канале",
                "content": digest_content
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка публикации еженедельного дайджеста: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ==================== АВТОМАТИЧЕСКАЯ ПУБЛИКАЦИЯ ====================
    
    async def auto_publish_approved_news(self) -> Dict[str, Any]:
        """
        Автоматически публикует одобренные новости.
        
        Returns:
            Dict с результатами автоматической публикации
        """
        try:
            logger.info("🤖 Автоматическая публикация одобренных новостей")
            
            # Получаем одобренные новости для публикации
            approved_news = await self._get_news_ready_for_publication()
            if not approved_news:
                logger.info("📝 Нет новостей для автоматической публикации")
                return {
                    "success": True,
                    "published": 0,
                    "message": "Нет новостей для публикации"
                }
            
            # Ограничиваем количество публикаций за раз
            news_to_publish = approved_news[:self.max_posts_per_day]
            
            # Публикуем новости
            results = await self.publish_news_batch([news.id for news in news_to_publish])
            
            logger.info(f"✅ Автоматическая публикация завершена: {results}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Ошибка автоматической публикации: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def start_auto_publication(self) -> bool:
        """
        Запускает автоматическую публикацию по расписанию.
        
        Returns:
            bool: True если автопубликация запущена успешно
        """
        try:
            logger.info("🚀 Запуск автоматической публикации по расписанию")
            
            # TODO: Реализовать планировщик
            # В реальной версии здесь будет asyncio.create_task() с планировщиком
            
            logger.info("✅ Автоматическая публикация запущена")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска автопубликации: {e}")
            return False
    
    # ==================== УПРАВЛЕНИЕ ОЧЕРЕДЬЮ ПУБЛИКАЦИЙ ====================
    
    async def get_publication_queue(self) -> List[Dict[str, Any]]:
        """
        Получает очередь публикаций.
        
        Returns:
            List с информацией о публикациях в очереди
        """
        try:
            # Получаем новости, готовые к публикации
            ready_news = await self._get_news_ready_for_publication()
            
            queue = []
            for news in ready_news:
                queue.append({
                    "news_id": news.id,
                    "title": news.title,
                    "status": news.status,
                    "created_at": news.created_at,
                    "priority": self._calculate_publication_priority(news)
                })
            
            return queue
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения очереди публикаций: {e}")
            return []
    
    async def schedule_publication(self, news_id: int, publish_at: datetime) -> bool:
        """
        Планирует публикацию новости на определенное время.
        
        Args:
            news_id: ID новости
            publish_at: Время публикации
            
        Returns:
            bool: True если публикация запланирована успешно
        """
        try:
            logger.info(f"📅 Планирование публикации новости {news_id} на {publish_at}")
            
            # TODO: Реализовать планировщик
            # В реальной версии здесь будет добавление в очередь планировщика
            
            # Обновляем статус новости
            await self._update_news_publication_status(news_id, PublicationStatus.SCHEDULED)
            
            logger.info(f"✅ Публикация новости {news_id} запланирована на {publish_at}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка планирования публикации: {e}")
            return False
    
    # ==================== СТАТИСТИКА ПУБЛИКАЦИЙ ====================
    
    async def get_publication_statistics(self) -> Dict[str, Any]:
        """
        Получает статистику публикаций.
        
        Returns:
            Dict со статистикой публикаций
        """
        try:
            # Получаем статистику из базы данных
            total_news = self.db.get_all_news()
            
            stats = {
                "total_news": len(total_news),
                "published_today": 0,
                "published_this_week": 0,
                "published_this_month": 0,
                "queue_size": 0,
                "auto_publication_enabled": self.auto_publish_enabled,
                "max_posts_per_day": self.max_posts_per_day,
                "publication_interval": f"{self.publication_interval} часа"
            }
            
            # Подсчитываем статистику по датам
            from datetime import datetime, timedelta
            
            today = datetime.now().date()
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)
            
            # Получаем все новости
            all_news = self.db.get_all_news()
            
            # Подсчитываем опубликованные новости по датам
            for news in all_news:
                if hasattr(news, 'channel_published_at') and news.channel_published_at:
                    news_date = news.channel_published_at.date()
                    
                    if news_date == today:
                        stats["published_today"] += 1
                    if news_date >= week_ago:
                        stats["published_this_week"] += 1
                    if news_date >= month_ago:
                        stats["published_this_month"] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики публикаций: {e}")
            return {"error": str(e)}
    
    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================
    
    async def _get_daily_news(self) -> List[News]:
        """Получает новости за сегодня."""
        try:
            # TODO: Реализовать получение новостей за день
            # В реальной версии здесь будет запрос к базе данных
            return []
        except Exception as e:
            logger.error(f"❌ Ошибка получения дневных новостей: {e}")
            return []
    
    async def _get_weekly_news(self) -> List[News]:
        """Получает новости за неделю."""
        try:
            # TODO: Реализовать получение новостей за неделю
            return []
        except Exception as e:
            logger.error(f"❌ Ошибка получения недельных новостей: {e}")
            return []
    
    async def _get_news_ready_for_publication(self) -> List[News]:
        """Получает новости, готовые к публикации."""
        try:
            # TODO: Реализовать получение новостей для публикации
            # В реальной версии здесь будет запрос к базе данных
            return []
        except Exception as e:
            logger.error(f"❌ Ошибка получения новостей для публикации: {e}")
            return []
    
    async def _update_news_publication_status(self, news_id: int, status: PublicationStatus) -> bool:
        """Обновляет статус публикации новости."""
        try:
            # Получаем сессию базы данных
            session = self.db.get_session()
            if session:
                try:
                    from src.models.database import News
                    from datetime import datetime
                    
                    # Находим новость
                    news = session.query(News).filter_by(id=news_id).first()
                    if news:
                        # Обновляем время публикации в канале
                        if status == PublicationStatus.PUBLISHED:
                            news.channel_published_at = datetime.utcnow()
                        
                        session.commit()
                        logger.info(f"✅ Статус публикации новости {news_id} обновлен")
                        return True
                    else:
                        logger.warning(f"⚠️ Новость {news_id} не найдена для обновления статуса")
                        return False
                finally:
                    session.close()
            else:
                logger.error("❌ Не удалось получить сессию базы данных")
                return False
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статуса публикации: {e}")
            return False
    
    def _calculate_publication_priority(self, news: News) -> int:
        """Вычисляет приоритет публикации новости."""
        try:
            priority = 5  # Базовый приоритет
            
            # Увеличиваем приоритет для важных новостей
            if hasattr(news, 'importance_score') and news.importance_score:
                if news.importance_score >= 8:
                    priority += 3
                elif news.importance_score >= 6:
                    priority += 2
                elif news.importance_score >= 4:
                    priority += 1
            
            # Увеличиваем приоритет для свежих новостей
            if news.created_at:
                hours_old = (datetime.now() - news.created_at).total_seconds() / 3600
                if hours_old < 1:
                    priority += 2
                elif hours_old < 6:
                    priority += 1
            
            return min(priority, 10)  # Максимальный приоритет 10
            
        except Exception as e:
            logger.error(f"❌ Ошибка вычисления приоритета: {e}")
            return 5
    
    async def _send_to_telegram_channel(self, message: str) -> Dict[str, Any]:
        """
        Отправляет сообщение в Telegram канал.
        
        Args:
            message: Текст сообщения для отправки
            
        Returns:
            Dict с результатом отправки
        """
        try:
            if not self.bot_token or not self.channel_id:
                return {
                    "success": False,
                    "error": "Не настроен токен бота или ID канала"
                }
            
            # Формируем URL для отправки сообщения
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            # Параметры сообщения
            params = {
                "chat_id": self.channel_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            # Отправляем сообщение
            connector = aiohttp.TCPConnector(ssl=False)  # Отключаем SSL проверку для тестирования
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(url, json=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("ok"):
                            logger.info(f"✅ Сообщение успешно отправлено в канал {self.channel_id}")
                            return {
                                "success": True,
                                "message_id": result["result"]["message_id"]
                            }
                        else:
                            error_msg = result.get("description", "Неизвестная ошибка")
                            logger.error(f"❌ Telegram API вернул ошибку: {error_msg}")
                            return {
                                "success": False,
                                "error": f"Telegram API: {error_msg}"
                            }
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ HTTP ошибка {response.status}: {error_text}")
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}"
                        }
        
        except Exception as e:
            logger.error(f"❌ Ошибка отправки в Telegram: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def publish_digest_with_photo(self, digest_text: str, photo_file_id: str) -> Dict[str, Any]:
        """
        Публикует дайджест с фото в канал.
        
        Args:
            digest_text: Текст дайджеста
            photo_file_id: ID фото файла в Telegram
            
        Returns:
            Dict с результатами публикации
        """
        try:
            logger.info(f"📤 Публикация дайджеста с фото в канал")
            
            if not self.bot_token or not self.channel_id:
                return {
                    "success": False,
                    "error": "Не настроен токен бота или ID канала"
                }
            
            # Формируем URL для отправки фото с подписью
            url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
            
            # Обрезаем текст для подписи (лимит Telegram: 1024 символа)
            max_caption_length = 1024
            if len(digest_text) > max_caption_length:
                # Обрезаем до 1020 символов и добавляем "..."
                caption_text = digest_text[:max_caption_length - 3] + "..."
                logger.info(f"📝 Текст подписи обрезан с {len(digest_text)} до {len(caption_text)} символов")
            else:
                caption_text = digest_text
            
            # Параметры сообщения
            params = {
                "chat_id": self.channel_id,
                "photo": photo_file_id,
                "caption": caption_text,
                "parse_mode": "Markdown"
            }
            
            # Отправляем сообщение
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(url, json=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("ok"):
                            logger.info(f"✅ Дайджест с фото успешно отправлен в канал {self.channel_id}")
                            return {
                                "success": True,
                                "message_id": result["result"]["message_id"]
                            }
                        else:
                            error_msg = result.get("description", "Неизвестная ошибка")
                            logger.error(f"❌ Telegram API вернул ошибку: {error_msg}")
                            return {
                                "success": False,
                                "error": f"Telegram API: {error_msg}"
                            }
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ HTTP ошибка {response.status}: {error_text}")
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}"
                        }
        
        except Exception as e:
            logger.error(f"❌ Ошибка публикации дайджеста с фото: {e}")
            return {
                "success": False,
                "error": str(e)
            }
