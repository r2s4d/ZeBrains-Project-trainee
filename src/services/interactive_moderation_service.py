#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive Moderation Service - сервис для интерактивной модерации дайджеста.
Управляет процессом модерации через inline кнопки Telegram.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ModerationSession:
    """Сессия модерации для конкретного пользователя."""
    user_id: int
    chat_id: int
    message_id: int
    news_items: List[Dict[str, Any]]
    removed_news_ids: List[int]
    created_at: datetime
    is_completed: bool = False

class InteractiveModerationService:
    """
    Сервис для интерактивной модерации дайджеста через inline кнопки.
    """
    
    def __init__(self):
        """Инициализация сервиса."""
        self.active_sessions: Dict[int, ModerationSession] = {}
        logger.info("✅ InteractiveModerationService инициализирован")
    
    def create_moderation_session(self, user_id: int, chat_id: int, message_id: int, news_items: List[Dict[str, Any]]) -> ModerationSession:
        """
        Создает новую сессию модерации.
        
        Args:
            user_id: ID пользователя-куратора
            chat_id: ID чата
            message_id: ID сообщения с дайджестом
            news_items: Список новостей для модерации
            
        Returns:
            ModerationSession: Созданная сессия
        """
        session = ModerationSession(
            user_id=user_id,
            chat_id=chat_id,
            message_id=message_id,
            news_items=news_items,
            removed_news_ids=[],
            created_at=datetime.now()
        )
        
        self.active_sessions[user_id] = session
        logger.info(f"✅ Создана сессия модерации для пользователя {user_id}")
        
        return session
    
    def remove_news_from_session(self, user_id: int, news_id: int) -> bool:
        """
        Удаляет новость из сессии модерации.
        
        Args:
            user_id: ID пользователя
            news_id: ID новости для удаления
            
        Returns:
            bool: True если новость удалена, False если не найдена
        """
        if user_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[user_id]
        
        # Проверяем, что новость еще не удалена
        if news_id in session.removed_news_ids:
            return False
        
        # Добавляем в список удаленных
        session.removed_news_ids.append(news_id)
        logger.info(f"✅ Новость {news_id} удалена из сессии пользователя {user_id}")
        
        return True
    
    def get_remaining_news(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Получает список оставшихся новостей в сессии.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            List: Список оставшихся новостей
        """
        if user_id not in self.active_sessions:
            return []
        
        session = self.active_sessions[user_id]
        remaining_news = [
            news for news in session.news_items 
            if news['id'] not in session.removed_news_ids
        ]
        
        return remaining_news
    
    def complete_moderation(self, user_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        Завершает модерацию и возвращает одобренные новости.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Optional[List]: Список одобренных новостей или None
        """
        if user_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[user_id]
        session.is_completed = True
        
        # Получаем одобренные новости
        approved_news = self.get_remaining_news(user_id)
        
        # НЕ удаляем сессию сразу - она нужна для передачи эксперту
        # Сессия будет удалена после отправки новостей эксперту
        
        logger.info(f"✅ Модерация завершена для пользователя {user_id}, одобрено {len(approved_news)} новостей")
        
        return approved_news
    
    def get_session_status(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает статус сессии модерации.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Optional[Dict]: Статус сессии или None
        """
        if user_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[user_id]
        
        return {
            "total_news": len(session.news_items),
            "removed_news": len(session.removed_news_ids),
            "remaining_news": len(self.get_remaining_news(user_id)),
            "is_completed": session.is_completed,
            "created_at": session.created_at
        }
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """
        Очищает старые сессии модерации.
        
        Args:
            max_age_hours: Максимальный возраст сессии в часах
        """
        current_time = datetime.now()
        sessions_to_remove = []
        
        for user_id, session in self.active_sessions.items():
            age = current_time - session.created_at
            if age.total_seconds() > max_age_hours * 3600:
                sessions_to_remove.append(user_id)
        
        for user_id in sessions_to_remove:
            del self.active_sessions[user_id]
            logger.info(f"🧹 Удалена старая сессия модерации для пользователя {user_id}")
        
        if sessions_to_remove:
            logger.info(f"🧹 Очищено {len(sessions_to_remove)} старых сессий модерации")
    
    def cleanup_moderation_session(self, user_id: int):
        """
        Очищает сессию модерации после отправки новостей эксперту.
        
        Args:
            user_id: ID пользователя
        """
        if user_id in self.active_sessions:
            del self.active_sessions[user_id]
            logger.info(f"🧹 Сессия модерации для пользователя {user_id} очищена после отправки эксперту")
        else:
            logger.warning(f"⚠️ Сессия модерации для пользователя {user_id} не найдена при очистке")

    async def remove_news_and_cleanup_digest(self, user_id: int, news_id: int, chat_id: str, morning_digest_service) -> List[Dict[str, Any]]:
        """
        Удаляет новость из сессии и очищает сообщения дайджеста.
        
        Args:
            user_id: ID пользователя
            news_id: ID новости для удаления
            chat_id: ID чата
            morning_digest_service: Сервис утреннего дайджеста
            
        Returns:
            List[Dict]: Список оставшихся новостей
        """
        try:
            # Удаляем новость из сессии
            success = self.remove_news_from_session(user_id, news_id)
            if not success:
                logger.warning(f"⚠️ Не удалось удалить новость {news_id} из сессии пользователя {user_id}")
            
            # Очищаем сообщения дайджеста
            if morning_digest_service:
                cleanup_success = await morning_digest_service.delete_digest_messages(chat_id)
                if cleanup_success:
                    logger.info(f"✅ Сообщения дайджеста очищены для чата {chat_id}")
                else:
                    logger.warning(f"⚠️ Не удалось очистить сообщения дайджеста для чата {chat_id}")
            
            # Получаем оставшиеся новости
            remaining_news = self.get_remaining_news(user_id)
            logger.info(f"📋 Оставшиеся новости после удаления: {len(remaining_news)}")
            
            return remaining_news
            
        except Exception as e:
            logger.error(f"❌ Ошибка удаления новости и очистки дайджеста: {e}")
            return []
