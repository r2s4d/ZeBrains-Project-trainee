#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Utilities - общие утилиты для работы с Telegram ботом.
Содержит переиспользуемые функции для обработки ошибок и проверок.
"""

import logging
from typing import Optional, Any
from telegram import CallbackQuery, Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class BotUtils:
    """Утилиты для работы с Telegram ботом."""
    
    @staticmethod
    async def safe_answer_callback(query: CallbackQuery, text: Optional[str] = None) -> bool:
        """
        Безопасно отвечает на callback query с обработкой ошибок.
        
        Args:
            query: CallbackQuery объект
            text: Текст ответа (опционально)
            
        Returns:
            bool: True если ответ успешен, False если ошибка
        """
        try:
            await query.answer(text)
            return True
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при ответе на callback query: {e}")
            return False
    
    @staticmethod
    async def check_service_availability(service: Any, service_name: str, query: CallbackQuery) -> bool:
        """
        Проверяет доступность сервиса с единообразной обработкой ошибок.
        
        Args:
            service: Объект сервиса для проверки
            service_name: Название сервиса для логирования
            query: CallbackQuery для ответа пользователю
            
        Returns:
            bool: True если сервис доступен, False если недоступен
        """
        if not hasattr(service, 'service') or not service.service:
            logger.error(f"❌ {service_name} недоступен")
            await BotUtils.safe_answer_callback(query, f"❌ {service_name} недоступен")
            return False
        return True
    
    @staticmethod
    async def check_service_availability_simple(service: Any, service_name: str, query: CallbackQuery) -> bool:
        """
        Упрощенная проверка доступности сервиса (без вложенного атрибута service).
        
        Args:
            service: Объект сервиса для проверки
            service_name: Название сервиса для логирования
            query: CallbackQuery для ответа пользователю
            
        Returns:
            bool: True если сервис доступен, False если недоступен
        """
        if not service:
            logger.error(f"❌ {service_name} недоступен")
            await BotUtils.safe_answer_callback(query, f"❌ {service_name} недоступен")
            return False
        return True
    
    @staticmethod
    async def handle_error_with_callback(error: Exception, query: CallbackQuery, 
                                       operation_name: str = "операция") -> None:
        """
        Обрабатывает ошибку с отправкой ответа пользователю.
        
        Args:
            error: Исключение
            query: CallbackQuery для ответа
            operation_name: Название операции для логирования
        """
        logger.error(f"❌ Ошибка в {operation_name}: {error}")
        await BotUtils.safe_answer_callback(query, "❌ Произошла ошибка")
    
    @staticmethod
    async def handle_error_with_message(error: Exception, update: Update, 
                                      operation_name: str = "операция") -> None:
        """
        Обрабатывает ошибку с отправкой сообщения пользователю.
        
        Args:
            error: Исключение
            update: Update объект
            operation_name: Название операции для логирования
        """
        logger.error(f"❌ Ошибка в {operation_name}: {error}")
        if update.message:
            await update.message.reply_text(
                f"❌ Произошла ошибка при {operation_name}:\n{str(error)}\n\n"
                "Попробуйте позже или обратитесь к администратору."
            )
    
    @staticmethod
    def extract_id_from_callback_data(callback_data: str, prefix: str) -> Optional[int]:
        """
        Извлекает ID из callback data.
        
        Args:
            callback_data: Данные callback
            prefix: Префикс для поиска (например, "remove_news_")
            
        Returns:
            int: Извлеченный ID или None если не найден
        """
        try:
            if callback_data.startswith(prefix):
                return int(callback_data.split("_")[-1])
        except (ValueError, IndexError) as e:
            logger.warning(f"⚠️ Ошибка извлечения ID из callback data '{callback_data}': {e}")
        return None
