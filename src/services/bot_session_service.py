#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BotSessionService - сервис для управления состояниями бота в базе данных.
Обеспечивает устойчивость к перезапускам и сбоям.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.models import BotSession, engine
from src.config import config

logger = logging.getLogger(__name__)


class BotSessionService:
    """
    Сервис для управления состояниями бота в базе данных.
    
    Этот сервис заменяет хранение состояний в памяти (словари типа self.waiting_for_digest_edit)
    на хранение в базе данных. Это обеспечивает устойчивость к перезапускам бота.
    """
    
    def __init__(self):
        """Инициализация сервиса."""
        self.engine = engine
        logger.info("✅ BotSessionService инициализирован")
    
    def get_session(self) -> Session:
        """Получает сессию базы данных."""
        return Session(bind=self.engine)
    
    async def save_session(self, 
                          session_type: str, 
                          user_id: Optional[str] = None,
                          chat_id: Optional[str] = None, 
                          data: Optional[Dict[str, Any]] = None,
                          status: str = 'active',
                          expires_at: Optional[datetime] = None) -> bool:
        """
        Сохраняет сессию в базе данных.
        
        Args:
            session_type: Тип сессии ('digest_edit', 'photo_wait', 'expert_session', etc.)
            user_id: ID пользователя (куратора, эксперта)
            chat_id: ID чата (для системных сессий)
            data: Данные сессии в виде словаря
            status: Статус сессии ('active', 'completed', 'expired', 'cancelled')
            expires_at: Время истечения сессии (для автоочистки)
            
        Returns:
            bool: True если успешно сохранено
        """
        try:
            with self.get_session() as session:
                # Проверяем, есть ли уже активная сессия этого типа для пользователя
                existing_session = session.query(BotSession).filter(
                    and_(
                        BotSession.session_type == session_type,
                        BotSession.user_id == user_id,
                        BotSession.status == 'active'
                    )
                ).first()
                
                if existing_session:
                    # Обновляем существующую сессию
                    existing_session.data = json.dumps(data or {})
                    existing_session.status = status
                    existing_session.expires_at = expires_at
                    existing_session.updated_at = datetime.now()
                    session.commit()
                    logger.debug(f"🔄 Обновлена сессия: {session_type} для пользователя {user_id}")
                else:
                    # Создаем новую сессию
                    new_session = BotSession(
                        session_type=session_type,
                        user_id=user_id,
                        chat_id=chat_id,
                        data=json.dumps(data or {}),
                        status=status,
                        expires_at=expires_at
                    )
                    session.add(new_session)
                    session.commit()
                    logger.debug(f"💾 Создана новая сессия: {session_type} для пользователя {user_id}")
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения сессии {session_type}: {e}")
            return False
    
    async def get_session_data(self, 
                              session_type: str, 
                              user_id: Optional[str] = None,
                              chat_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Получает данные сессии из базы данных.
        
        Args:
            session_type: Тип сессии
            user_id: ID пользователя
            chat_id: ID чата
            
        Returns:
            Dict с данными сессии или None если не найдено
        """
        try:
            with self.get_session() as session:
                query = session.query(BotSession).filter(
                    BotSession.session_type == session_type,
                    BotSession.status == 'active'
                )
                
                if user_id:
                    query = query.filter(BotSession.user_id == user_id)
                if chat_id:
                    query = query.filter(BotSession.chat_id == chat_id)
                
                bot_session = query.first()
                
                if bot_session:
                    # Проверяем, не истекла ли сессия
                    current_time = datetime.now()
                    if bot_session.expires_at and bot_session.expires_at < current_time:
                        logger.debug(f"⏰ Сессия {session_type} истекла")
                        bot_session.status = 'expired'
                        session.commit()
                        return None
                    
                    data = json.loads(bot_session.data)
                    logger.debug(f"🎯 Получена сессия: {session_type} для пользователя {user_id}")
                    return data
                
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения сессии {session_type}: {e}")
            return None
    
    async def update_session_data(self, 
                                 session_type: str, 
                                 user_id: Optional[str] = None,
                                 chat_id: Optional[str] = None,
                                 data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Обновляет данные существующей сессии.
        
        Args:
            session_type: Тип сессии
            user_id: ID пользователя
            chat_id: ID чата
            data: Новые данные сессии
            
        Returns:
            bool: True если успешно обновлено
        """
        try:
            with self.get_session() as session:
                query = session.query(BotSession).filter(
                    BotSession.session_type == session_type,
                    BotSession.status == 'active'
                )
                
                if user_id:
                    query = query.filter(BotSession.user_id == user_id)
                if chat_id:
                    query = query.filter(BotSession.chat_id == chat_id)
                
                bot_session = query.first()
                
                if bot_session:
                    bot_session.data = json.dumps(data or {})
                    bot_session.updated_at = datetime.now()
                    session.commit()
                    logger.debug(f"🔄 Обновлены данные сессии: {session_type}")
                    return True
                else:
                    logger.warning(f"⚠️ Сессия не найдена для обновления: {session_type}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Ошибка обновления сессии {session_type}: {e}")
            return False
    
    async def delete_session(self, 
                           session_type: str, 
                           user_id: Optional[str] = None,
                           chat_id: Optional[str] = None) -> bool:
        """
        Удаляет сессию из базы данных.
        
        Args:
            session_type: Тип сессии
            user_id: ID пользователя
            chat_id: ID чата
            
        Returns:
            bool: True если успешно удалено
        """
        try:
            with self.get_session() as session:
                query = session.query(BotSession).filter(
                    BotSession.session_type == session_type,
                    BotSession.status == 'active'
                )
                
                if user_id:
                    query = query.filter(BotSession.user_id == user_id)
                if chat_id:
                    query = query.filter(BotSession.chat_id == chat_id)
                
                bot_session = query.first()
                
                if bot_session:
                    bot_session.status = 'completed'
                    bot_session.updated_at = datetime.now()
                    session.commit()
                    logger.debug(f"🗑️ Сессия завершена: {session_type}")
                    return True
                else:
                    logger.warning(f"⚠️ Сессия не найдена для удаления: {session_type}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Ошибка удаления сессии {session_type}: {e}")
            return False
    
    async def get_active_sessions(self, session_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Получает все активные сессии.
        
        Args:
            session_type: Фильтр по типу сессии (если None - все типы)
            
        Returns:
            List[Dict]: Список активных сессий
        """
        try:
            with self.get_session() as session:
                query = session.query(BotSession).filter(BotSession.status == 'active')
                
                if session_type:
                    query = query.filter(BotSession.session_type == session_type)
                
                sessions = query.all()
                
                result = []
                for bot_session in sessions:
                    session_data = {
                        'id': bot_session.id,
                        'session_type': bot_session.session_type,
                        'user_id': bot_session.user_id,
                        'chat_id': bot_session.chat_id,
                        'data': json.loads(bot_session.data),
                        'status': bot_session.status,
                        'expires_at': bot_session.expires_at,
                        'created_at': bot_session.created_at,
                        'updated_at': bot_session.updated_at
                    }
                    result.append(session_data)
                
                logger.debug(f"📊 Найдено {len(result)} активных сессий")
                return result
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения активных сессий: {e}")
            return []
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Очищает истекшие сессии.
        
        Returns:
            int: Количество удаленных сессий
        """
        try:
            with self.get_session() as session:
                current_time = datetime.now()
                
                # Находим истекшие сессии
                expired_sessions = session.query(BotSession).filter(
                    and_(
                        BotSession.status == 'active',
                        BotSession.expires_at < current_time
                    )
                ).all()
                
                # Помечаем их как истекшие
                for bot_session in expired_sessions:
                    bot_session.status = 'expired'
                    bot_session.updated_at = current_time
                
                session.commit()
                
                count = len(expired_sessions)
                if count > 0:
                    logger.info(f"🧹 Очищено {count} истекших сессий")
                
                return count
                
        except Exception as e:
            logger.error(f"❌ Ошибка очистки истекших сессий: {e}")
            return 0
    
    async def cleanup_old_completed_sessions(self, days_old: int = 7) -> int:
        """
        Очищает старые завершенные сессии.
        
        Args:
            days_old: Количество дней, после которых сессии считаются старыми
            
        Returns:
            int: Количество удаленных сессий
        """
        try:
            with self.get_session() as session:
                cutoff_date = datetime.now() - timedelta(days=days_old)
                
                # Находим старые завершенные сессии
                old_sessions = session.query(BotSession).filter(
                    and_(
                        BotSession.status == 'completed',
                        BotSession.updated_at < cutoff_date
                    )
                ).all()
                
                # Удаляем их
                for bot_session in old_sessions:
                    session.delete(bot_session)
                
                session.commit()
                
                count = len(old_sessions)
                if count > 0:
                    logger.info(f"🧹 Очищено {count} старых завершенных сессий (старше {days_old} дней)")
                
                return count
                
        except Exception as e:
            logger.error(f"❌ Ошибка очистки старых сессий: {e}")
            return 0
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """
        Получает статистику сессий.
        
        Returns:
            Dict: Статистика сессий
        """
        try:
            with self.get_session() as session:
                # Общее количество сессий
                total_sessions = session.query(BotSession).count()
                
                # Активные сессии
                active_sessions = session.query(BotSession).filter(
                    BotSession.status == 'active'
                ).count()
                
                # Истекшие сессии
                expired_sessions = session.query(BotSession).filter(
                    BotSession.status == 'expired'
                ).count()
                
                # Завершенные сессии
                completed_sessions = session.query(BotSession).filter(
                    BotSession.status == 'completed'
                ).count()
                
                # Сессии по типам
                session_types = {}
                for session_type in ['digest_edit', 'photo_wait', 'expert_session', 'curator_moderation', 'current_digest', 'expert_comment']:
                    count = session.query(BotSession).filter(
                        BotSession.session_type == session_type
                    ).count()
                    session_types[session_type] = count
                
                return {
                    'total_sessions': total_sessions,
                    'active_sessions': active_sessions,
                    'expired_sessions': expired_sessions,
                    'completed_sessions': completed_sessions,
                    'session_types': session_types
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики сессий: {e}")
            return {}


# Глобальный экземпляр сервиса
bot_session_service = BotSessionService()
