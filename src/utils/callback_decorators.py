"""
Декораторы для автоматической обработки callback_query.
Обеспечивают правильное использование query.answer().
"""

import logging
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

def auto_answer_callback(default_message: str = "Обработано"):
    """
    Декоратор для автоматического ответа на callback_query.
    
    Args:
        default_message: Сообщение по умолчанию для query.answer()
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            query = update.callback_query
            
            # Автоматически отвечаем на callback query
            try:
                await query.answer(default_message)
            except Exception as e:
                logger.warning(f"⚠️ Ошибка при ответе на callback query в {func.__name__}: {e}")
                # Продолжаем выполнение даже если не удалось ответить
            
            # Выполняем основную функцию
            return await func(self, update, context)
        return wrapper
    return decorator

def require_curator_permissions(func):
    """
    Декоратор для проверки прав куратора перед выполнением callback.
    """
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user = update.effective_user
        
        # Проверяем права куратора
        if not await self._is_curator(user.id):
            await query.answer("❌ У вас нет прав для выполнения этой операции!")
            return
        
        # Выполняем основную функцию
        return await func(self, update, context)
    return wrapper

def safe_callback_execution(func):
    """
    Декоратор для безопасного выполнения callback с обработкой ошибок.
    """
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        
        try:
            return await func(self, update, context)
        except Exception as e:
            logger.error(f"❌ Ошибка в callback {func.__name__}: {e}")
            try:
                await query.answer("❌ Произошла ошибка при обработке запроса")
            except:
                pass  # Игнорируем ошибки ответа на callback
            raise
    return wrapper

