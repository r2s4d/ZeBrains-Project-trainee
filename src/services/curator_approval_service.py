# -*- coding: utf-8 -*-
"""
CuratorApprovalService - сервис для согласования дайджестов с куратором

Этот сервис отправляет финальный дайджест в кураторский чат для согласования
и обрабатывает ответы куратора (одобрение или правки).

Основные функции:
- Отправка дайджеста в кураторский чат
- Разделение длинных сообщений
- Интерактивные кнопки для согласования
- Обработка правок куратора
- Интеграция с системой публикации
"""

from src.config import config

import asyncio
import logging
import aiohttp
from typing import List, Dict, Optional, Any
from datetime import datetime

from src.services.final_digest_formatter_service import FinalDigestFormatterService

# Настройка логирования
logger = logging.getLogger(__name__)

class CuratorApprovalService:
    """
    Сервис для согласования дайджестов с куратором.
    
    Отправляет финальный дайджест в кураторский чат и обрабатывает
    ответы куратора (одобрение или внесение правок).
    """
    
    def __init__(self, bot_token: str, curator_chat_id: str, formatter_service: FinalDigestFormatterService, bot_instance=None):
        """
        Инициализация сервиса.
        
        Args:
            bot_token: Токен Telegram бота
            curator_chat_id: ID кураторского чата
            formatter_service: Сервис форматирования дайджестов
            bot_instance: Ссылка на экземпляр бота для управления состоянием
        """
        self.bot_token = bot_token
        self.curator_chat_id = curator_chat_id
        self.formatter_service = formatter_service
        self.bot_instance = bot_instance
        
        # Настройки
        self.max_message_length = config.message.max_digest_length
        self.approval_timeout = config.timeout.approval_timeout
        
        # Хранение текущего дайджеста для публикации
        self.current_digest_text = None
        
        logger.info(f"CuratorApprovalService инициализирован для чата {curator_chat_id}")
    
    async def send_digest_for_approval(
        self, 
        formatted_digest: str,
        chat_id: str
    ) -> Dict[str, Any]:
        """
        Отправляет дайджест в кураторский чат для согласования.
        
        Args:
            formatted_digest: Готовый отформатированный дайджест
            chat_id: ID чата для отправки
            
        Returns:
            Результат отправки
        """
        try:
            logger.info("📤 Отправка дайджеста на согласование куратору")
            
            # Сохраняем текст дайджеста для возможной публикации
            self.current_digest_text = formatted_digest
            logger.info(f"💾 Сохранен текст дайджеста: {len(formatted_digest)} символов")
            
            # 1. Разделяем на части если нужно
            digest_parts = self.formatter_service.split_digest_message(formatted_digest)
            
            # 2. Отправляем части дайджеста
            sent_messages = []
            for i, part in enumerate(digest_parts):
                message_text = part
                if len(digest_parts) > 1:
                    message_text = f"**Часть {i+1} из {len(digest_parts)}**\n\n{part}"
                
                result = await self._send_message_to_curator(message_text, chat_id)
                if result["success"]:
                    sent_messages.append(result["message_id"])
                else:
                    logger.error(f"❌ Ошибка отправки части {i+1}: {result['error']}")
                    return {
                        "success": False,
                        "error": f"Ошибка отправки части {i+1}: {result['error']}"
                    }
            
            # 3. Отправляем кнопки согласования
            approval_result = await self._send_approval_buttons(chat_id)
            if not approval_result["success"]:
                logger.error(f"❌ Ошибка отправки кнопок: {approval_result['error']}")
                return approval_result
            
            logger.info("✅ Дайджест отправлен на согласование куратору")
            return {
                "success": True,
                "message_ids": sent_messages,
                "approval_message_id": approval_result["message_id"],
                "digest": formatted_digest
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки дайджеста на согласование: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _send_message_to_curator(self, message: str, chat_id: str = None) -> Dict[str, Any]:
        """
        Отправляет сообщение в кураторский чат.
        
        Args:
            message: Текст сообщения
            chat_id: ID чата (если не указан, используется curator_chat_id)
            
        Returns:
            Результат отправки
        """
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            target_chat_id = chat_id or self.curator_chat_id
            
            params = {
                "chat_id": target_chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            connector = aiohttp.TCPConnector(ssl=True)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(url, json=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("ok"):
                            return {
                                "success": True,
                                "message_id": result["result"]["message_id"]
                            }
                        else:
                            error_msg = result.get("description", "Неизвестная ошибка")
                            return {
                                "success": False,
                                "error": f"Telegram API: {error_msg}"
                            }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}"
                        }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _send_approval_buttons(self, chat_id: str = None) -> Dict[str, Any]:
        """
        Отправляет кнопки согласования в кураторский чат.
        
        Args:
            chat_id: ID чата (если не указан, используется curator_chat_id)
        
        Returns:
            Результат отправки
        """
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            target_chat_id = chat_id or self.curator_chat_id
            
            message_text = """
**📋 Дайджест готов к публикации!**

Пожалуйста, проверьте дайджест и выберите действие:

✅ **Одобрить** - дайджест будет опубликован в канал
✏️ **Внести правки** - вы сможете отредактировать текст
            """
            
            # Создаем inline клавиатуру
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "✅ Одобрить",
                            "callback_data": "approve_digest"
                        },
                        {
                            "text": "✏️ Внести правки", 
                            "callback_data": "edit_digest"
                        }
                    ]
                ]
            }
            
            params = {
                "chat_id": target_chat_id,
                "text": message_text,
                "parse_mode": "Markdown",
                "reply_markup": keyboard
            }
            
            connector = aiohttp.TCPConnector(ssl=True)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(url, json=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("ok"):
                            return {
                                "success": True,
                                "message_id": result["result"]["message_id"]
                            }
                        else:
                            error_msg = result.get("description", "Неизвестная ошибка")
                            return {
                                "success": False,
                                "error": f"Telegram API: {error_msg}"
                            }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}"
                        }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def handle_approval(self, callback_data: str, user_id: str) -> Dict[str, Any]:
        """
        Обрабатывает ответ куратора на согласование.
        
        Args:
            callback_data: Данные callback (approve_digest или edit_digest)
            user_id: ID пользователя
            
        Returns:
            Результат обработки
        """
        try:
            logger.info(f"🔍 handle_approval: callback_data={callback_data}, current_digest_text={self.current_digest_text is not None}")
            if callback_data == "approve_digest":
                return await self._handle_digest_approval(user_id)
            elif callback_data == "edit_digest":
                return await self._handle_digest_editing(user_id)
            elif callback_data == "approve_edited_digest":
                return await self._handle_edited_digest_approval(user_id)
            else:
                return {
                    "success": False,
                    "error": "Неизвестный callback"
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки согласования: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _handle_digest_approval(self, user_id: str) -> Dict[str, Any]:
        """
        Обрабатывает одобрение дайджеста куратором.
        
        Args:
            user_id: ID куратора
            
        Returns:
            Результат обработки
        """
        try:
            logger.info(f"✅ Куратор {user_id} одобрил дайджест")
            
            # Устанавливаем состояние ожидания фото в боте
            logger.info(f"🔍 Диагностика: bot_instance={self.bot_instance is not None}, current_digest_text={self.current_digest_text is not None}")
            if self.current_digest_text:
                logger.info(f"📝 Текст дайджеста: {self.current_digest_text[:100]}...")
            if self.bot_instance and self.current_digest_text:
                self.bot_instance.waiting_for_photo[int(user_id)] = self.current_digest_text
                logger.info(f"🔄 Установлено состояние ожидания фото для пользователя {user_id}")
            else:
                logger.error(f"❌ Не удалось установить состояние ожидания фото: bot_instance={self.bot_instance is not None}, current_digest_text={self.current_digest_text is not None}")
            
            # Отправляем подтверждение
            confirmation_message = """
✅ **Дайджест одобрен!**

Теперь нужно добавить фото для поста. Пожалуйста, отправьте изображение.
            """
            
            result = await self._send_message_to_curator(confirmation_message, self.curator_chat_id)
            
            if result["success"]:
                return {
                    "success": True,
                    "action": "request_photo",
                    "message": "Дайджест одобрен, ожидаем фото"
                }
            else:
                return {
                    "success": False,
                    "error": f"Ошибка отправки подтверждения: {result['error']}"
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки одобрения: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _handle_digest_editing(self, user_id: str) -> Dict[str, Any]:
        """
        Обрабатывает запрос на редактирование дайджеста.
        
        Args:
            user_id: ID куратора
            
        Returns:
            Результат обработки
        """
        try:
            logger.info(f"✏️ Куратор {user_id} запросил редактирование дайджеста")
            
            # Отправляем инструкции для редактирования
            edit_message = """
✏️ **Редактирование дайджеста**

Пожалуйста, отправьте исправленный текст дайджеста.

**Инструкции:**
- Сохраните структуру (заголовок, введение, новости, заключение)
- Используйте Markdown форматирование
- После отправки исправленного текста дайджест будет пересоздан
            """
            
            result = await self._send_message_to_curator(edit_message)
            
            if result["success"]:
                return {
                    "success": True,
                    "action": "wait_for_edit",
                    "message": "Ожидаем исправленный текст"
                }
            else:
                return {
                    "success": False,
                    "error": f"Ошибка отправки инструкций: {result['error']}"
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки редактирования: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _handle_edited_digest_approval(self, user_id: str) -> Dict[str, Any]:
        """
        Обрабатывает одобрение исправленного дайджеста.
        
        Args:
            user_id: ID куратора
            
        Returns:
            Результат обработки
        """
        try:
            logger.info(f"✅ Куратор {user_id} одобрил исправленный дайджест")
            
            # Устанавливаем состояние ожидания фото в боте
            if self.bot_instance and self.current_digest_text:
                self.bot_instance.waiting_for_photo[int(user_id)] = self.current_digest_text
                logger.info(f"🔄 Установлено состояние ожидания фото для пользователя {user_id}")
            
            # Отправляем запрос на фото для публикации
            result = await self._send_message_to_curator(
                "📸 Отлично! Дайджест одобрен. Пожалуйста, отправьте фото для публикации в канал.",
                self.curator_chat_id
            )
            
            if result["success"]:
                return {
                    "success": True,
                    "action": "photo_request",
                    "message": "Запрос на фото отправлен"
                }
            else:
                return {
                    "success": False,
                    "error": f"Ошибка отправки запроса на фото: {result['error']}"
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки одобрения исправленного дайджеста: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def process_edited_digest(self, edited_text: str, user_id: str) -> Dict[str, Any]:
        """
        Обрабатывает исправленный дайджест от куратора.
        
        Args:
            edited_text: Исправленный текст дайджеста
            user_id: ID куратора
            
        Returns:
            Результат обработки
        """
        try:
            logger.info(f"📝 Обработка исправленного дайджеста от куратора {user_id}")
            
            # Проверяем грамматику исправленного текста
            corrected_text = self.formatter_service.check_grammar_and_punctuation(edited_text)
            
            # Сохраняем исправленный текст дайджеста для возможной публикации
            self.current_digest_text = corrected_text
            
            # Отправляем исправленный дайджест обратно для финального одобрения
            logger.info("📤 Вызываем _send_edited_digest_for_final_approval")
            result = await self._send_edited_digest_for_final_approval(corrected_text)
            logger.info(f"📤 Результат отправки исправленного дайджеста: {result}")
            
            if result["success"]:
                return {
                    "success": True,
                    "action": "final_approval",
                    "corrected_digest": corrected_text,
                    "message": f"✅ Правки обработаны! Исправленный дайджест отправлен на согласование.\n\n📝 Исправленный текст:\n\n{corrected_text}"
                }
            else:
                return {
                    "success": False,
                    "error": f"Ошибка отправки исправленного дайджеста: {result['error']}"
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки исправленного дайджеста: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _send_edited_digest_for_final_approval(self, corrected_digest: str) -> Dict[str, Any]:
        """
        Отправляет исправленный дайджест на финальное одобрение.
        
        Args:
            corrected_digest: Исправленный дайджест
            
        Returns:
            Результат отправки
        """
        try:
            logger.info(f"📤 Отправка исправленного дайджеста в кураторский чат {self.curator_chat_id}")
            
            # Отправляем исправленный дайджест с кнопками одним сообщением
            result = await self._send_edited_digest_with_buttons(corrected_digest)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _send_edited_digest_with_buttons(self, corrected_digest: str) -> Dict[str, Any]:
        """
        Отправляет исправленный дайджест с кнопками одним сообщением.
        
        Args:
            corrected_digest: Исправленный дайджест
            
        Returns:
            Результат отправки
        """
        try:
            import aiohttp
            
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            # Создаем сообщение с исправленным дайджестом
            message_text = f"**📋 Исправленный дайджест готов!**\n\n{corrected_digest}\n\nПожалуйста, проверьте исправления и выберите действие:"
            
            logger.info(f"📝 Отправляемое сообщение (длина: {len(message_text)}): {message_text[:200]}...")
            
            # Создаем inline клавиатуру
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "✅ Одобрить",
                            "callback_data": "approve_edited_digest"
                        },
                        {
                            "text": "🔄 Еще раз отредактировать",
                            "callback_data": "edit_digest_again"
                        }
                    ]
                ]
            }
            
            params = {
                "chat_id": self.curator_chat_id,
                "text": message_text,
                "parse_mode": "Markdown",
                "reply_markup": keyboard
            }
            
            connector = aiohttp.TCPConnector(ssl=True)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(url, json=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"📤 Ответ Telegram API: {result}")
                        if result.get("ok"):
                            logger.info("✅ Исправленный дайджест с кнопками отправлен успешно")
                            return {
                                "success": True,
                                "message_id": result["result"]["message_id"]
                            }
                        else:
                            logger.error(f"❌ Ошибка Telegram API: {result}")
                            return {
                                "success": False,
                                "error": f"Telegram API error: {result}"
                            }
                    else:
                        logger.error(f"❌ HTTP ошибка: {response.status}")
                        return {
                            "success": False,
                            "error": f"HTTP error: {response.status}"
                        }
                        
        except Exception as e:
            logger.error(f"❌ Ошибка отправки исправленного дайджеста: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
