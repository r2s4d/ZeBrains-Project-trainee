"""
Утилиты для работы с таймаутами в асинхронных операциях.
Предотвращают блокировку event loop.
"""

import asyncio
import logging
from typing import Any, Callable, Optional
from functools import wraps

logger = logging.getLogger(__name__)

class TimeoutError(Exception):
    """Исключение для таймаутов."""
    pass

async def with_timeout(
    coro: Any, 
    timeout_seconds: float, 
    operation_name: str = "операция",
    fallback_value: Any = None
) -> Any:
    """
    Выполняет асинхронную операцию с таймаутом.
    
    Args:
        coro: Асинхронная операция для выполнения
        timeout_seconds: Таймаут в секундах
        operation_name: Название операции для логирования
        fallback_value: Значение по умолчанию при таймауте
        
    Returns:
        Результат операции или fallback_value при таймауте
        
    Raises:
        TimeoutError: При превышении таймаута
    """
    try:
        result = await asyncio.wait_for(coro, timeout=timeout_seconds)
        logger.debug(f"✅ {operation_name} выполнена за {timeout_seconds}с")
        return result
        
    except asyncio.TimeoutError:
        logger.warning(f"⏰ Таймаут {operation_name} ({timeout_seconds}с)")
        if fallback_value is not None:
            logger.info(f"🔄 Используем fallback значение для {operation_name}")
            return fallback_value
        else:
            raise TimeoutError(f"Таймаут {operation_name} ({timeout_seconds}с)")
            
    except Exception as e:
        logger.error(f"❌ Ошибка в {operation_name}: {e}")
        if fallback_value is not None:
            logger.info(f"🔄 Используем fallback значение для {operation_name}")
            return fallback_value
        else:
            raise

def timeout_decorator(timeout_seconds: float, operation_name: str = "операция", fallback_value: Any = None):
    """
    Декоратор для добавления таймаута к асинхронным функциям.
    
    Args:
        timeout_seconds: Таймаут в секундах
        operation_name: Название операции для логирования
        fallback_value: Значение по умолчанию при таймауте
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await with_timeout(
                func(*args, **kwargs),
                timeout_seconds,
                operation_name,
                fallback_value
            )
        return wrapper
    return decorator

# Предустановленные таймауты для разных типов операций
AI_REQUEST_TIMEOUT = 30.0  # 30 секунд для AI запросов
HTTP_REQUEST_TIMEOUT = 60.0  # 60 секунд для HTTP запросов
DATABASE_TIMEOUT = 10.0  # 10 секунд для операций с БД
TELEGRAM_API_TIMEOUT = 30.0  # 30 секунд для Telegram API

# Декораторы для разных типов операций
ai_timeout = timeout_decorator(AI_REQUEST_TIMEOUT, "AI запрос", None)
http_timeout = timeout_decorator(HTTP_REQUEST_TIMEOUT, "HTTP запрос", None)
db_timeout = timeout_decorator(DATABASE_TIMEOUT, "операция с БД", None)
telegram_timeout = timeout_decorator(TELEGRAM_API_TIMEOUT, "Telegram API", None)

