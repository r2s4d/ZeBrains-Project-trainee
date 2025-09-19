#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive Moderation Service - сервис для интерактивной модерации дайджеста.
Управляет процессом модерации через inline кнопки Telegram.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from src.services.bot_session_service import bot_session_service

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
        # Используем BotSessionService для управления состояниями
        self.session_service = bot_session_service
        logger.info("✅ InteractiveModerationService инициализирован")
    
    async def _save_moderation_session(self, session: ModerationSession) -> bool:
        """
        Сохраняет сессию модерации в БД.
        
        Args:
            session: Объект сессии модерации
            
        Returns:
            bool: True если успешно сохранено
        """
        try:
            session_data = {
                'user_id': session.user_id,
                'chat_id': session.chat_id,
                'message_id': session.message_id,
                'news_items': session.news_items,
                'removed_news': session.removed_news_ids,
                'is_completed': session.is_completed,
                'created_at': session.created_at.isoformat() if session.created_at else datetime.now().isoformat()
            }
            
            return await self.session_service.save_session(
                session_type='moderation_session',
                user_id=str(session.user_id),
                data=session_data,
                expires_at=datetime.now() + timedelta(hours=4)  # 4 часа на модерацию
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения сессии модерации {session.user_id}: {e}")
            return False
    
    async def _get_moderation_session(self, user_id: int) -> Optional[ModerationSession]:
        """
        Получает сессию модерации из БД.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            ModerationSession или None если не найдено
        """
        try:
            session_data = await self.session_service.get_session_data(
                session_type='moderation_session',
                user_id=str(user_id)
            )
            
            if not session_data:
                return None
            
            # Восстанавливаем объект ModerationSession из данных БД
            session = ModerationSession(
                user_id=session_data['user_id'],
                chat_id=session_data['chat_id'],
                message_id=session_data['message_id'],
                news_items=session_data['news_items'],
                removed_news_ids=session_data['removed_news'],
                is_completed=session_data['is_completed'],
                created_at=datetime.fromisoformat(session_data['created_at']) if session_data.get('created_at') else datetime.now()
            )
            
            return session
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения сессии модерации {user_id}: {e}")
            return None
    
    async def _delete_moderation_session(self, user_id: int) -> bool:
        """
        Удаляет сессию модерации из БД.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            bool: True если успешно удалено
        """
        try:
            return await self.session_service.delete_session(
                session_type='moderation_session',
                user_id=str(user_id)
            )
        except Exception as e:
            logger.error(f"❌ Ошибка удаления сессии модерации {user_id}: {e}")
            return False
    
    async def create_moderation_session(self, user_id: int, chat_id: int, message_id: int, news_items: List[Dict[str, Any]]) -> ModerationSession:
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
        
        # Сохраняем сессию в БД вместо памяти
        await self._save_moderation_session(session)
        logger.info(f"✅ Создана сессия модерации для пользователя {user_id}")
        
        return session
    
    async def remove_news_from_session(self, user_id: int, news_id: int) -> bool:
        """
        Удаляет новость из сессии модерации.
        
        Args:
            user_id: ID пользователя
            news_id: ID новости для удаления
            
        Returns:
            bool: True если новость удалена, False если не найдена
        """
        # Получаем сессию из БД
        session = await self._get_moderation_session(user_id)
        if not session:
            return False
        
        # Проверяем, что новость еще не удалена
        if news_id in session.removed_news_ids:
            return False
        
        # Добавляем в список удаленных
        session.removed_news_ids.append(news_id)
        
        # Сохраняем обновленную сессию в БД
        await self._save_moderation_session(session)
        logger.info(f"✅ Новость {news_id} удалена из сессии пользователя {user_id}")
        
        return True
    
    async def get_remaining_news(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Получает список оставшихся новостей в сессии.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            List: Список оставшихся новостей
        """
        # Получаем сессию из БД
        session = await self._get_moderation_session(user_id)
        if not session:
            return []
        
        remaining_news = [
            news for news in session.news_items 
            if news['id'] not in session.removed_news_ids
        ]
        
        return remaining_news
    
    async def complete_moderation(self, user_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        Завершает модерацию и возвращает одобренные новости.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Optional[List]: Список одобренных новостей или None
        """
        # Получаем сессию из БД
        session = await self._get_moderation_session(user_id)
        if not session:
            return None
        
        session.is_completed = True
        
        # Получаем одобренные новости
        approved_news = await self.get_remaining_news(user_id)
        
        # Сохраняем обновленную сессию в БД
        await self._save_moderation_session(session)
        
        # НЕ удаляем сессию сразу - она нужна для передачи эксперту
        # Сессия будет удалена после отправки новостей эксперту
        
        logger.info(f"✅ Модерация завершена для пользователя {user_id}, одобрено {len(approved_news)} новостей")
        
        return approved_news
    
    async def cleanup_moderation_session(self, user_id: int):
        """
        Очищает сессию модерации после отправки новостей эксперту.
        
        Args:
            user_id: ID пользователя
        """
        # Удаляем сессию из БД
        success = await self._delete_moderation_session(user_id)
        if success:
            logger.info(f"🧹 Сессия модерации для пользователя {user_id} очищена после отправки эксперту")
        else:
            logger.warning(f"⚠️ Сессия модерации для пользователя {user_id} не найдена при очистке")

