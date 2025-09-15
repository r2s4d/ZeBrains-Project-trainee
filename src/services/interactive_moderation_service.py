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

