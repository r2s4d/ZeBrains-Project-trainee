"""
Утилиты для retry механизмов и circuit breaker.
Обеспечивают надежность сетевых операций.
"""

import asyncio
import logging
import time
from typing import Any, Callable, Optional
from functools import wraps
from enum import Enum

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Состояния circuit breaker."""
    CLOSED = "CLOSED"      # Нормальная работа
    OPEN = "OPEN"          # Блокировка запросов
    HALF_OPEN = "HALF_OPEN"  # Тестирование восстановления

class CircuitBreaker:
    """
    Circuit Breaker для защиты от каскадных отказов.
    """
    
    def __init__(
        self, 
        failure_threshold: int = 5, 
        timeout: int = 60,
        expected_exception: type = Exception
    ):
        """
        Инициализация circuit breaker.
        
        Args:
            failure_threshold: Количество ошибок для открытия circuit
            timeout: Время блокировки в секундах
            expected_exception: Тип исключения для отслеживания
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        
        logger.info(f"🔧 Circuit Breaker инициализирован: threshold={failure_threshold}, timeout={timeout}s")
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Выполняет функцию через circuit breaker.
        
        Args:
            func: Функция для выполнения
            *args: Аргументы функции
            **kwargs: Именованные аргументы функции
            
        Returns:
            Результат выполнения функции
            
        Raises:
            CircuitBreakerOpenException: Если circuit открыт
        """
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info("🔄 Circuit Breaker переходит в состояние HALF_OPEN")
            else:
                raise CircuitBreakerOpenException("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Обработка успешного выполнения."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        logger.debug("✅ Circuit Breaker: успешное выполнение")
    
    def _on_failure(self):
        """Обработка ошибки выполнения."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(f"🔴 Circuit Breaker ОТКРЫТ после {self.failure_count} сбоев")
        else:
            logger.warning(f"⚠️ Circuit Breaker: {self.failure_count}/{self.failure_threshold} сбоев")

class CircuitBreakerOpenException(Exception):
    """Исключение для открытого circuit breaker."""
    pass

def retry_on_failure(
    max_retries: int = 3, 
    delay: float = 1.0, 
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Декоратор для повтора операций при сбоях.
    
    Args:
        max_retries: Максимальное количество повторов
        delay: Начальная задержка в секундах
        backoff: Коэффициент увеличения задержки
        exceptions: Типы исключений для повтора
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        wait_time = delay * (backoff ** attempt)
                        logger.warning(f"🔄 Попытка {attempt + 1}/{max_retries + 1} не удалась: {e}. Повтор через {wait_time:.1f}с")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"❌ Все {max_retries + 1} попыток не удались. Последняя ошибка: {e}")
                        
            raise last_exception
            
        return wrapper
    return decorator

def with_circuit_breaker(
    failure_threshold: int = 5,
    timeout: int = 60,
    expected_exception: type = Exception
):
    """
    Декоратор для добавления circuit breaker к функции.
    
    Args:
        failure_threshold: Количество ошибок для открытия circuit
        timeout: Время блокировки в секундах
        expected_exception: Тип исключения для отслеживания
    """
    circuit_breaker = CircuitBreaker(failure_threshold, timeout, expected_exception)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await circuit_breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator

# Предустановленные конфигурации для разных типов операций
AI_RETRY_CONFIG = {
    'max_retries': 3,
    'delay': 2.0,
    'backoff': 2.0,
    'exceptions': (Exception,)
}

HTTP_RETRY_CONFIG = {
    'max_retries': 2,
    'delay': 1.0,
    'backoff': 1.5,
    'exceptions': (ConnectionError, TimeoutError, asyncio.TimeoutError)
}

DATABASE_RETRY_CONFIG = {
    'max_retries': 3,
    'delay': 0.5,
    'backoff': 2.0,
    'exceptions': (Exception,)
}

# Декораторы для разных типов операций
ai_retry = retry_on_failure(**AI_RETRY_CONFIG)
http_retry = retry_on_failure(**HTTP_RETRY_CONFIG)
db_retry = retry_on_failure(**DATABASE_RETRY_CONFIG)

# Circuit breakers для разных сервисов
ai_circuit_breaker = with_circuit_breaker(
    failure_threshold=3,
    timeout=300,  # 5 минут
    expected_exception=Exception
)

http_circuit_breaker = with_circuit_breaker(
    failure_threshold=5,
    timeout=180,  # 3 минуты
    expected_exception=ConnectionError
)

