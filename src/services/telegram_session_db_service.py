#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сервис для работы с Telegram User API сессиями в БД
Использует существующую таблицу bot_sessions с уровнем защиты 1+2

Особенности:
- Использует bot_sessions таблицу (не создаем новую)
- session_type = 'telegram_user_session' 
- Все данные в JSON поле data (зашифрованы)
- Интеграция с TelegramSecurityService
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.models.database import BotSession
from src.services.database_singleton import get_database_service
from src.services.telegram_security_service import TelegramSecurityService

logger = logging.getLogger(__name__)

class TelegramSessionDBService:
    """
    Сервис для безопасной работы с Telegram User API сессиями в БД
    
    Использует существующую таблицу bot_sessions:
    - session_type = 'telegram_user_session'
    - user_id = хэш номера телефона  
    - data = зашифрованный JSON с данными сессии
    """
    
    def __init__(self):
        """Инициализация сервиса"""
        self.db = get_database_service()
        self.security = TelegramSecurityService()
        self.session_type = 'telegram_user_session'
        logger.info("🗄️ Сервис БД сессий инициализирован")
    
    async def save_session(
        self, 
        session_name: str, 
        phone: str, 
        session_data: bytes,
        expires_in_days: int = 30
    ) -> int:
        """
        Сохраняет зашифрованную Telegram User API сессию в БД
        
        Args:
            session_name: Имя сессии (например, "AI_News_Curator")
            phone: Номер телефона (например, "+79161234567")
            session_data: Данные сессии от Telethon (bytes)
            expires_in_days: Срок действия сессии в днях
            
        Returns:
            int: ID сохраненной записи в БД
            
        Raises:
            Exception: При ошибках шифрования или сохранения
        """
        try:
            logger.info(f"💾 Сохранение сессии: {session_name}")
            
            # Создаем зашифрованную JSON структуру
            data_json = self.security.create_session_data_json(phone, session_data)
            data_json_str = json.dumps(data_json, ensure_ascii=False)
            
            # Хэшируем номер для user_id (для быстрого поиска)
            phone_hash = self.security.hash_phone_number(phone)
            
            # Вычисляем время истечения
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
            
            with self.db.get_session() as db_session:
                # Проверяем, есть ли уже сессия с таким ЖЕ ИМЕНЕМ
                existing_session = db_session.query(BotSession).filter_by(
                    session_type=self.session_type,
                    chat_id=session_name  # Ищем по имени сессии, НЕ по номеру!
                ).first()
                
                if existing_session:
                    # Обновляем существующую сессию с тем же именем
                    existing_session.user_id = phone_hash  # Обновляем хэш номера
                    existing_session.data = data_json_str
                    existing_session.status = 'active'
                    existing_session.expires_at = expires_at
                    existing_session.updated_at = datetime.utcnow()
                    
                    session_id = existing_session.id
                    logger.info(f"🔄 Обновлена сессия с именем '{session_name}' (ID: {session_id})")
                    
                else:
                    # Создаем новую сессию
                    new_session = BotSession(
                        session_type=self.session_type,
                        user_id=phone_hash,  # Хэш номера, НЕ реальный номер!
                        chat_id=session_name,  # Используем chat_id для имени сессии
                        data=data_json_str,
                        status='active',
                        expires_at=expires_at
                    )
                    
                    db_session.add(new_session)
                    db_session.flush()  # Получаем ID
                    
                    session_id = new_session.id
                    logger.info(f"✅ Создана новая сессия: {session_name} (ID: {session_id})")
                
                db_session.commit()
                return session_id
                
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения сессии '{session_name}': {e}")
            raise
    
    async def load_session_by_name(self, session_name: str) -> Optional[bytes]:
        """
        Загружает сессию по имени
        
        Args:
            session_name: Имя сессии (например, "AI_News_Curator")
            
        Returns:
            bytes: Расшифрованные данные сессии или None если не найдена
        """
        try:
            with self.db.get_session() as db_session:
                session_record = db_session.query(BotSession).filter_by(
                    session_type=self.session_type,
                    chat_id=session_name,  # Имя сессии в chat_id
                    status='active'
                ).first()
                
                if not session_record:
                    logger.warning(f"⚠️ Сессия не найдена: {session_name}")
                    return None
                
                return await self._extract_session_data(session_record, db_session)
                
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки сессии '{session_name}': {e}")
            return None
    
    async def load_session_by_phone(self, phone: str) -> Optional[bytes]:
        """
        Загружает сессию по номеру телефона
        
        Args:
            phone: Номер телефона (например, "+79161234567")
            
        Returns:
            bytes: Расшифрованные данные сессии или None если не найдена
        """
        try:
            # Хэшируем номер для поиска
            phone_hash = self.security.hash_phone_number(phone)
            
            with self.db.get_session() as db_session:
                session_record = db_session.query(BotSession).filter_by(
                    session_type=self.session_type,
                    user_id=phone_hash,
                    status='active'
                ).first()
                
                if not session_record:
                    logger.warning(f"⚠️ Сессия не найдена для номера: {phone[:4]}******")
                    return None
                
                return await self._extract_session_data(session_record, db_session)
                
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки сессии по номеру: {e}")
            return None
    
    async def _extract_session_data(self, session_record: BotSession, db_session: Session) -> Optional[bytes]:
        """
        Извлекает и расшифровывает данные сессии из записи БД
        
        Args:
            session_record: Запись из БД
            db_session: Сессия БД для обновлений
            
        Returns:
            bytes: Расшифрованные данные сессии
        """
        try:
            # Проверяем срок действия
            if session_record.expires_at and session_record.expires_at < datetime.utcnow():
                logger.warning(f"⏰ Сессия истекла: {session_record.chat_id}")
                session_record.status = 'expired'
                db_session.commit()
                return None
            
            # Парсим JSON данные
            data_json = json.loads(session_record.data)
            
            # Валидируем данные
            if not self.security.validate_session_data(data_json):
                logger.warning(f"⚠️ Невалидные данные сессии: {session_record.chat_id}")
                session_record.status = 'invalid'
                db_session.commit()
                return None
            
            # Расшифровываем данные сессии
            session_data = self.security.extract_session_data_from_json(data_json)
            
            # Обновляем время последнего использования и данные
            session_record.updated_at = datetime.utcnow()
            session_record.data = json.dumps(data_json, ensure_ascii=False)  # Сохраняем обновленную статистику
            db_session.commit()
            
            logger.info(f"🔓 Сессия успешно загружена: {session_record.chat_id}")
            return session_data
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения данных сессии: {e}")
            # Сохраняем ошибку в данных сессии
            try:
                data_json = json.loads(session_record.data)
                data_json["last_error"] = str(e)
                session_record.data = json.dumps(data_json, ensure_ascii=False)
                session_record.status = 'error'
                db_session.commit()
            except:
                pass  # Игнорируем ошибки при сохранении ошибки
            
            return None
    
    async def deactivate_session(self, session_name: str, reason: str = "manual") -> bool:
        """
        Деактивирует сессию (при выходе или ошибке)
        
        Args:
            session_name: Имя сессии
            reason: Причина деактивации
            
        Returns:
            bool: True если сессия была деактивирована
        """
        try:
            with self.db.get_session() as db_session:
                session_record = db_session.query(BotSession).filter_by(
                    session_type=self.session_type,
                    chat_id=session_name
                ).first()
                
                if session_record:
                    session_record.status = 'deactivated'
                    session_record.updated_at = datetime.utcnow()
                    
                    # Добавляем причину в данные
                    try:
                        data_json = json.loads(session_record.data)
                        data_json["deactivation_reason"] = reason
                        data_json["deactivated_at"] = datetime.utcnow().isoformat()
                        session_record.data = json.dumps(data_json, ensure_ascii=False)
                    except:
                        pass  # Игнорируем ошибки с JSON
                    
                    db_session.commit()
                    logger.info(f"🔒 Сессия деактивирована: {session_name} (причина: {reason})")
                    return True
                else:
                    logger.warning(f"⚠️ Сессия для деактивации не найдена: {session_name}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Ошибка деактивации сессии '{session_name}': {e}")
            return False
    
    async def list_active_sessions(self) -> List[Dict[str, Any]]:
        """
        Возвращает список всех активных Telegram User API сессий
        
        Returns:
            List[Dict]: Список сессий с основной информацией (БЕЗ секретных данных)
        """
        try:
            with self.db.get_session() as db_session:
                sessions = db_session.query(BotSession).filter_by(
                    session_type=self.session_type,
                    status='active'
                ).all()
                
                result = []
                for session in sessions:
                    try:
                        data_json = json.loads(session.data)
                        
                        session_info = {
                            "id": session.id,
                            "name": session.chat_id,
                            "phone_hash": data_json.get("phone_hash", "unknown")[:8] + "...",  # Только первые 8 символов
                            "usage_count": data_json.get("usage_count", 0),
                            "created_at": session.created_at.isoformat() if session.created_at else None,
                            "last_used_at": session.updated_at.isoformat() if session.updated_at else None,
                            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
                            "last_error": data_json.get("last_error")
                        }
                        result.append(session_info)
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка обработки сессии {session.id}: {e}")
                        continue
                
                logger.info(f"📋 Найдено активных сессий: {len(result)}")
                return result
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка сессий: {e}")
            return []
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Очищает истекшие сессии (вызывается периодически)
        
        Returns:
            int: Количество очищенных сессий
        """
        try:
            with self.db.get_session() as db_session:
                # Находим истекшие сессии
                expired_sessions = db_session.query(BotSession).filter(
                    BotSession.session_type == self.session_type,
                    BotSession.expires_at < datetime.utcnow(),
                    BotSession.status == 'active'
                ).all()
                
                count = 0
                for session in expired_sessions:
                    session.status = 'expired'
                    session.updated_at = datetime.utcnow()
                    count += 1
                
                db_session.commit()
                
                if count > 0:
                    logger.info(f"🧹 Очищено истекших сессий: {count}")
                
                return count
                
        except Exception as e:
            logger.error(f"❌ Ошибка очистки истекших сессий: {e}")
            return 0
    
    async def get_session_statistics(self) -> Dict[str, Any]:
        """
        Возвращает статистику по всем Telegram User API сессиям
        
        Returns:
            Dict: Статистика сессий
        """
        try:
            with self.db.get_session() as db_session:
                # Считаем сессии по статусам
                stats = {
                    "active": 0,
                    "expired": 0,
                    "deactivated": 0,
                    "error": 0,
                    "total": 0
                }
                
                sessions = db_session.query(BotSession).filter_by(
                    session_type=self.session_type
                ).all()
                
                total_usage = 0
                for session in sessions:
                    stats["total"] += 1
                    stats[session.status] = stats.get(session.status, 0) + 1
                    
                    # Считаем общее использование
                    try:
                        data_json = json.loads(session.data)
                        total_usage += data_json.get("usage_count", 0)
                    except:
                        pass
                
                stats["total_usage"] = total_usage
                stats["average_usage"] = total_usage / max(stats["total"], 1)
                
                logger.info(f"📊 Статистика сессий: {stats['active']} активных из {stats['total']} общих")
                return stats
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {"error": str(e)}
