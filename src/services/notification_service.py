#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NotificationService - сервис для отправки уведомлений экспертам и кураторам

Этот сервис:
1. Отправляет уведомления о новых заданиях
2. Напоминает о невыполненных задачах
3. Уведомляет о статусе новостей
4. Интегрируется с Telegram API для отправки сообщений
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from enum import Enum

from src.services.database_service import DatabaseService
from src.models.database import News, Curator, Expert, Comment

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationType(Enum):
    """Типы уведомлений."""
    NEW_NEWS_FOR_CURATOR = "new_news_for_curator"
    NEWS_APPROVED_FOR_EXPERT = "news_approved_for_expert"
    EXPERT_COMMENT_RECEIVED = "expert_comment_received"
    NEWS_READY_FOR_PUBLICATION = "news_ready_for_publication"
    REMINDER_UNFINISHED_TASK = "reminder_unfinished_task"
    DAILY_DIGEST = "daily_digest"

class NotificationPriority(Enum):
    """Приоритеты уведомлений."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class NotificationService:
    """
    Сервис для отправки уведомлений экспертам и кураторам.
    
    Основные функции:
    - Отправка уведомлений о новых заданиях
    - Напоминания о невыполненных задачах
    - Уведомления о статусе новостей
    - Ежедневные дайджесты
    """
    
    def __init__(self, database_service: DatabaseService):
        """
        Инициализация сервиса.
        
        Args:
            database_service: Сервис для работы с базой данных
        """
        self.db = database_service
        
        # Настройки уведомлений
        self.reminder_interval = 4  # часа
        self.max_retries = 3
        self.batch_size = 10
        
        logger.info("NotificationService инициализирован")
    
    # ==================== УВЕДОМЛЕНИЯ ДЛЯ КУРАТОРОВ ====================
    
    async def notify_curator_new_news(self, curator_id: int, news: News) -> bool:
        """
        Уведомляет куратора о новой новости для проверки.
        
        Args:
            curator_id: ID куратора
            news: Новость для проверки
            
        Returns:
            bool: True если уведомление отправлено успешно
        """
        try:
            curator = self.db.get_curator_by_id(curator_id)
            if not curator:
                logger.warning(f"⚠️ Куратор {curator_id} не найден")
                return False
            
            # Формируем сообщение
            message = self._format_curator_notification(news)
            
            # TODO: Отправка через Telegram API
            # В реальной версии здесь будет отправка сообщения
            logger.info(f"📨 Уведомление куратору {curator.name}: {news.title[:50]}...")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления куратора: {e}")
            return False
    
    async def notify_curators_batch(self, news_list: List[News]) -> Dict[str, int]:
        """
        Уведомляет кураторов о новых новостях пакетно.
        
        Args:
            news_list: Список новостей для уведомления
            
        Returns:
            Dict с результатами отправки
        """
        logger.info(f"📨 Пакетное уведомление кураторов о {len(news_list)} новостях")
        
        results = {"success": 0, "failed": 0, "total": len(news_list)}
        
        for news in news_list:
            try:
                # Назначаем куратора (пока простой алгоритм)
                curator_id = await self._assign_curator_to_news(news.id)
                if curator_id:
                    success = await self.notify_curator_new_news(curator_id, news)
                    if success:
                        results["success"] += 1
                    else:
                        results["failed"] += 1
                else:
                    results["failed"] += 1
                    
            except Exception as e:
                logger.error(f"❌ Ошибка уведомления о новости {news.id}: {e}")
                results["failed"] += 1
        
        logger.info(f"✅ Пакетное уведомление завершено: {results}")
        return results
    
    # ==================== УВЕДОМЛЕНИЯ ДЛЯ ЭКСПЕРТОВ ====================
    
    async def notify_expert_new_assignment(self, expert_id: int, news: News) -> bool:
        """
        Уведомляет эксперта о новом задании.
        
        Args:
            expert_id: ID эксперта
            news: Новость для экспертизы
            
        Returns:
            bool: True если уведомление отправлено успешно
        """
        try:
            expert = self.db.get_expert_by_id(expert_id)
            if not expert:
                logger.warning(f"⚠️ Эксперт {expert_id} не найден")
                return False
            
            # Формируем сообщение
            message = self._format_expert_assignment_notification(news)
            
            # TODO: Отправка через Telegram API
            logger.info(f"📨 Уведомление эксперту {expert.name}: {news.title[:50]}...")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления эксперта: {e}")
            return False
    
    async def notify_experts_batch(self, news_list: List[News]) -> Dict[str, int]:
        """
        Уведомляет экспертов о новых заданиях пакетно.
        
        Args:
            news_list: Список новостей для экспертизы
            
        Returns:
            Dict с результатами отправки
        """
        logger.info(f"📨 Пакетное уведомление экспертов о {len(news_list)} заданиях")
        
        results = {"success": 0, "failed": 0, "total": len(news_list)}
        
        for news in news_list:
            try:
                # Назначаем эксперта
                expert_id = await self._assign_expert_to_news(news.id)
                if expert_id:
                    success = await self.notify_expert_new_assignment(expert_id, news)
                    if success:
                        results["success"] += 1
                    else:
                        results["failed"] += 1
                else:
                    results["failed"] += 1
                    
            except Exception as e:
                logger.error(f"❌ Ошибка уведомления о задании {news.id}: {e}")
                results["failed"] += 1
        
        logger.info(f"✅ Пакетное уведомление экспертов завершено: {results}")
        return results
    
    # ==================== НАПОМИНАНИЯ И РЕМИНДЕРЫ ====================
    
    async def send_reminders_unfinished_tasks(self) -> Dict[str, int]:
        """
        Отправляет напоминания о невыполненных задачах.
        
        Returns:
            Dict с результатами отправки напоминаний
        """
        logger.info("⏰ Отправка напоминаний о невыполненных задачах")
        
        results = {"curators": 0, "experts": 0, "total": 0}
        
        try:
            # Напоминания кураторам
            curator_reminders = await self._get_curator_reminders()
            for reminder in curator_reminders:
                await self._send_curator_reminder(reminder)
                results["curators"] += 1
            
            # Напоминания экспертам
            expert_reminders = await self._get_expert_reminders()
            for reminder in expert_reminders:
                await self._send_expert_reminder(reminder)
                results["experts"] += 1
            
            results["total"] = results["curators"] + results["experts"]
            logger.info(f"✅ Напоминания отправлены: {results}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки напоминаний: {e}")
        
        return results
    
    async def send_daily_digest(self) -> bool:
        """
        Отправляет ежедневный дайджест всем участникам.
        
        Returns:
            bool: True если дайджест отправлен успешно
        """
        try:
            logger.info("📊 Отправка ежедневного дайджеста")
            
            # Получаем статистику за день
            daily_stats = await self._get_daily_statistics()
            
            # Формируем дайджест
            digest_message = self._format_daily_digest(daily_stats)
            
            # Отправляем кураторам
            curators = self.db.get_all_curators()
            for curator in curators:
                await self._send_daily_digest_to_curator(curator, digest_message)
            
            # Отправляем экспертам
            experts = self.db.get_all_experts()
            for expert in experts:
                await self._send_daily_digest_to_expert(expert, digest_message)
            
            logger.info("✅ Ежедневный дайджест отправлен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки ежедневного дайджеста: {e}")
            return False
    
    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================
    
    def _format_curator_notification(self, news: News) -> str:
        """Форматирует уведомление для куратора."""
        return f"""
🔍 **Новая новость для проверки**

📰 **Заголовок:** {news.title}
📝 **Содержание:** {news.content[:200]}...
📅 **Дата:** {news.created_at.strftime('%d.%m.%Y %H:%M')}
🆔 **ID новости:** {news.id}

⚠️ **Требует вашего внимания!**
        """.strip()
    
    def _format_expert_assignment_notification(self, news: News) -> str:
        """Форматирует уведомление о задании для эксперта."""
        return f"""
🎯 **Новое задание для экспертизы**

📰 **Заголовок:** {news.title}
📝 **Содержание:** {news.content[:200]}...
📅 **Дата:** {news.created_at.strftime('%d.%m.%Y %H:%M')}
⭐ **Важность:** {getattr(news, 'importance_score', 'Не определена')}

💡 **Ваше мнение важно для сообщества!**
        """.strip()
    
    def _format_daily_digest(self, stats: Dict[str, Any]) -> str:
        """Форматирует ежедневный дайджест."""
        return f"""
📊 **Ежедневный дайджест AI News Assistant**

📅 **Дата:** {datetime.now().strftime('%d.%m.%Y')}

📰 **Статистика за день:**
• Новых новостей: {stats.get('new_news', 0)}
• Проверено кураторами: {stats.get('curated_news', 0)}
• Получено экспертных комментариев: {stats.get('expert_comments', 0)}
• Готово к публикации: {stats.get('ready_for_publication', 0)}

🚀 **Продолжайте отличную работу!**
        """.strip()
    
    async def _assign_curator_to_news(self, news_id: int) -> Optional[int]:
        """Назначает куратора к новости."""
        try:
            # Простой алгоритм: первый доступный куратор
            curators = self.db.get_all_curators()
            if curators:
                return curators[0].id
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка назначения куратора: {e}")
            return None
    
    async def _assign_expert_to_news(self, news_id: int) -> Optional[int]:
        """Назначает эксперта к новости."""
        try:
            # Простой алгоритм: первый доступный эксперт
            experts = self.db.get_all_experts()
            if experts:
                return experts[0].id
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка назначения эксперта: {e}")
            return None
    
    async def _get_curator_reminders(self) -> List[Dict[str, Any]]:
        """Получает список напоминаний для кураторов."""
        try:
            # TODO: Реализовать логику получения напоминаний
            return []
        except Exception as e:
            logger.error(f"❌ Ошибка получения напоминаний кураторов: {e}")
            return []
    
    async def _get_expert_reminders(self) -> List[Dict[str, Any]]:
        """Получает список напоминаний для экспертов."""
        try:
            # TODO: Реализовать логику получения напоминаний
            return []
        except Exception as e:
            logger.error(f"❌ Ошибка получения напоминаний экспертов: {e}")
            return []
    
    async def _get_daily_statistics(self) -> Dict[str, Any]:
        """Получает статистику за день."""
        try:
            # TODO: Реализовать получение статистики
            return {
                "new_news": 0,
                "curated_news": 0,
                "expert_comments": 0,
                "ready_for_publication": 0
            }
        except Exception as e:
            logger.error(f"❌ Ошибка получения дневной статистики: {e}")
            return {}
    
    async def _send_curator_reminder(self, reminder: Dict[str, Any]) -> bool:
        """Отправляет напоминание куратору."""
        # TODO: Реализовать отправку
        return True
    
    async def _send_expert_reminder(self, reminder: Dict[str, Any]) -> bool:
        """Отправляет напоминание эксперту."""
        # TODO: Реализовать отправку
        return True
    
    async def _send_daily_digest_to_curator(self, curator: Curator, message: str) -> bool:
        """Отправляет ежедневный дайджест куратору."""
        # TODO: Реализовать отправку
        return True
    
    async def _send_daily_digest_to_expert(self, expert: Expert, message: str) -> bool:
        """Отправляет ежедневный дайджест эксперту."""
        # TODO: Реализовать отправку
        return True
    
    async def send_telegram_message(self, chat_id: str, message: str, parse_mode: str = "HTML") -> bool:
        """
        Отправляет сообщение в Telegram чат.
        
        Args:
            chat_id: ID чата или username
            message: Текст сообщения
            parse_mode: Режим парсинга (HTML, Markdown)
            
        Returns:
            bool: True если сообщение отправлено успешно
        """
        try:
            # TODO: В реальной версии здесь будет отправка через Telegram API
            # Пока просто логируем
            logger.info(f"📤 Отправка в Telegram чат {chat_id}: {message[:100]}...")
            
            # Для тестирования считаем, что отправка прошла успешно
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки в Telegram: {e}")
            return False
