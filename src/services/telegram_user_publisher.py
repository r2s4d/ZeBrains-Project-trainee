#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сервис публикации через Telegram User API (Telethon)
Решает проблему ограничений Bot API для длинных сообщений

Преимущества User API над Bot API:
- Подпись к фото: до 4096 символов (Premium) вместо 1024


"""

import asyncio
import logging
from typing import Optional, Union, List, Dict, Any
from pathlib import Path

# Telethon для User API
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError, 
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    FloodWaitError,
    ChatWriteForbiddenError
)
from telethon.tl.types import InputPeerChannel, InputPeerChat

from src.services.telegram_session_db_service import TelegramSessionDBService
from src.config.settings import config

logger = logging.getLogger(__name__)

class TelegramUserPublisher:
    """
    Сервис публикации через Telegram User API
    
    Использует:
    - Telethon для User API (вместо python-telegram-bot)
    - Зашифрованные сессии в БД (вместо файлов)
    - Premium аккаунт для снятия ограничений
    """
    
    def __init__(self, session_name: Optional[str] = None):
        """
        Инициализация издателя
        
        Args:
            session_name: Имя сессии в БД (по умолчанию из config)
        """
        # Используем session_name из параметра или из конфигурации
        self.session_name = session_name or config.telegram.user_session_name
        self.session_db = TelegramSessionDBService()
        self.client: Optional[TelegramClient] = None
        self.is_connected = False
        
        # API credentials из конфигурации
        self.api_id = config.telegram.api_id if hasattr(config.telegram, 'api_id') else None
        self.api_hash = config.telegram.api_hash if hasattr(config.telegram, 'api_hash') else None
        
        if not self.api_id or not self.api_hash:
            logger.error("❌ TELEGRAM_API_ID и TELEGRAM_API_HASH не настроены!")
            logger.error("📋 Получите их на https://my.telegram.org/apps")
            raise ValueError("User API credentials не настроены")
        
        logger.info(f"🔧 Инициализирован TelegramUserPublisher: {session_name}")
    
    async def connect(self) -> bool:
        """
        Подключается к Telegram User API используя сессию из БД
        
        Returns:
            bool: True если подключение успешно
        """
        try:
            if self.is_connected:
                logger.info("✅ Уже подключен к User API")
                return True
            
            logger.info(f"🔌 Подключение к Telegram User API: {self.session_name}")
            
            # Загружаем сессию из БД
            session_data = await self.session_db.load_session_by_name(self.session_name)
            
            if not session_data:
                logger.error(f"❌ Сессия не найдена: {self.session_name}")
                logger.error("📋 Сначала нужно создать сессию через setup_user_session.py")
                return False
            
            # Создаем Telethon клиент с данными из БД
            # Преобразуем байты обратно в строку для Telethon
            session_string = session_data.decode('utf-8')
            
            # Используем StringSession для работы с данными из БД
            string_session = StringSession(session_string)
            
            self.client = TelegramClient(
                session=string_session,  # Используем StringSession объект
                api_id=self.api_id,
                api_hash=self.api_hash
            )
            
            # Подключаемся
            await self.client.start()
            
            # Проверяем авторизацию
            me = await self.client.get_me()
            logger.info(f"✅ Подключен как: {me.first_name} {me.last_name or ''} (@{me.username or 'без_username'})")
            
            self.is_connected = True
            return True
            
        except SessionPasswordNeededError:
            logger.error("❌ Требуется пароль двухфакторной аутентификации")
            logger.error("📋 Настройте 2FA или пересоздайте сессию")
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к User API: {e}")
            return False
    
    async def disconnect(self):
        """Отключается от Telegram User API"""
        try:
            if self.client and self.is_connected:
                await self.client.disconnect()
                logger.info("🔌 Отключен от User API")
            
            self.is_connected = False
            self.client = None
            
        except Exception as e:
            logger.error(f"❌ Ошибка отключения: {e}")
    
    async def publish_digest(
        self, 
        channel_id: str, 
        content: str, 
        photo_path: Optional[str] = None,
        silent: bool = False
    ) -> Optional[str]:
        """
        Публикует дайджест в канал через User API
        
        Args:
            channel_id: ID канала (@channel или -100123456789)
            content: Полный текст дайджеста (до 4096 символов для Premium)
            photo_path: Путь к фото (опционально)
            silent: Тихая публикация (без уведомлений)
            
        Returns:
            str: URL опубликованного сообщения или None при ошибке
        """
        try:
            # Проверяем подключение
            if not await self.connect():
                return None
            
            logger.info(f"📤 Публикация дайджеста в {channel_id}")
            logger.info(f"📝 Длина текста: {len(content)} символов")
            
            # Получаем entity канала
            try:
                channel_entity = await self.client.get_entity(channel_id)
                logger.info(f"📢 Канал найден: {channel_entity.title}")
            except Exception as e:
                logger.error(f"❌ Канал не найден: {channel_id} - {e}")
                return None
            
            # Публикуем сообщение
            if photo_path and Path(photo_path).exists():
                # С фото и полным текстом в подписи (до 4096 символов!)
                logger.info(f"📸 Публикация с фото: {photo_path}")
                
                message = await self.client.send_file(
                    entity=channel_entity,
                    file=photo_path,
                    caption=content,
                    parse_mode='html',
                    silent=silent
                )
                
                logger.info("✅ Опубликовано: фото + полный текст в подписи")
                
            else:
                # Только текст (до 4096 символов)
                logger.info("📝 Публикация только текста")
                
                message = await self.client.send_message(
                    entity=channel_entity,
                    message=content,
                    parse_mode='html',
                    silent=silent
                )
                
                logger.info("✅ Опубликовано: только текст")
            
            # Формируем URL сообщения
            if hasattr(channel_entity, 'username') and channel_entity.username:
                message_url = f"https://t.me/{channel_entity.username}/{message.id}"
            else:
                # Для приватных каналов используем ID
                channel_id_clean = str(channel_entity.id).replace('-100', '')
                message_url = f"https://t.me/c/{channel_id_clean}/{message.id}"
            
            logger.info(f"🔗 Ссылка на пост: {message_url}")
            return message_url
            
        except ChatWriteForbiddenError:
            logger.error(f"❌ Нет прав на публикацию в канале: {channel_id}")
            return None
            
        except FloodWaitError as e:
            logger.error(f"❌ Ограничение Telegram: подождите {e.seconds} секунд")
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка публикации дайджеста: {e}")
            return None
    
    async def publish_media_group(
        self,
        channel_id: str,
        content: str,
        media_paths: List[str],
        silent: bool = False
    ) -> Optional[str]:
        """
        Публикует медиа-группу (несколько фото) с текстом
        
        Args:
            channel_id: ID канала
            content: Текст (будет подписью к первому фото)
            media_paths: Список путей к фото (до 10 штук)
            silent: Тихая публикация
            
        Returns:
            str: URL первого сообщения в группе
        """
        try:
            if not await self.connect():
                return None
            
            logger.info(f"📸 Публикация медиа-группы: {len(media_paths)} фото")
            
            # Проверяем файлы
            valid_files = []
            for path in media_paths[:10]:  # Максимум 10 фото
                if Path(path).exists():
                    valid_files.append(path)
                else:
                    logger.warning(f"⚠️ Файл не найден: {path}")
            
            if not valid_files:
                logger.error("❌ Нет валидных файлов для публикации")
                return None
            
            # Получаем entity канала
            channel_entity = await self.client.get_entity(channel_id)
            
            # Публикуем медиа-группу
            # Первое фото с подписью, остальные без подписи
            messages = await self.client.send_file(
                entity=channel_entity,
                file=valid_files,
                caption=content if len(content) <= 1024 else content[:1024],  # Ограничение для медиа-группы
                parse_mode='html',
                silent=silent
            )
            
            # Получаем первое сообщение для URL
            first_message = messages[0] if isinstance(messages, list) else messages
            
            # Формируем URL
            if hasattr(channel_entity, 'username') and channel_entity.username:
                message_url = f"https://t.me/{channel_entity.username}/{first_message.id}"
            else:
                channel_id_clean = str(channel_entity.id).replace('-100', '')
                message_url = f"https://t.me/c/{channel_id_clean}/{first_message.id}"
            
            logger.info(f"✅ Медиа-группа опубликована: {len(valid_files)} фото")
            logger.info(f"🔗 Ссылка: {message_url}")
            
            return message_url
            
        except Exception as e:
            logger.error(f"❌ Ошибка публикации медиа-группы: {e}")
            return None
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Тестирует подключение и возвращает информацию о пользователе
        
        Returns:
            Dict: Информация о подключении и пользователе
        """
        try:
            if not await self.connect():
                return {"success": False, "error": "Не удалось подключиться"}
            
            # Получаем информацию о себе
            me = await self.client.get_me()
            
            result = {
                "success": True,
                "user_id": me.id,
                "first_name": me.first_name,
                "last_name": me.last_name,
                "username": me.username,
                "phone": me.phone,
                "is_premium": getattr(me, 'premium', False),
                "session_name": self.session_name
            }
            
            logger.info(f"✅ Тест подключения успешен: {me.first_name}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка теста подключения: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_channel_info(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о канале
        
        Args:
            channel_id: ID канала
            
        Returns:
            Dict: Информация о канале
        """
        try:
            if not await self.connect():
                return None
            
            channel = await self.client.get_entity(channel_id)
            
            return {
                "id": channel.id,
                "title": channel.title,
                "username": getattr(channel, 'username', None),
                "participants_count": getattr(channel, 'participants_count', None),
                "about": getattr(channel, 'about', None),
                "can_send_messages": not getattr(channel, 'broadcast', True)  # True для групп, False для каналов
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о канале: {e}")
            return None
    
    def __del__(self):
        """Деструктор - автоматически отключается при удалении объекта"""
        if self.is_connected:
            try:
                asyncio.create_task(self.disconnect())
            except:
                pass  # Игнорируем ошибки при завершении
