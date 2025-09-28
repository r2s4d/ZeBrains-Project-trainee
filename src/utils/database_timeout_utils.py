"""
Утилиты для работы с таймаутами в операциях с базой данных.
Обеспечивают асинхронное выполнение синхронных SQLAlchemy операций.
"""

import asyncio
import logging
from typing import Any, Callable, List, Optional
from concurrent.futures import ThreadPoolExecutor
from src.utils.timeout_utils import with_timeout, DATABASE_TIMEOUT

logger = logging.getLogger(__name__)

class DatabaseTimeoutManager:
    """Менеджер для выполнения операций с БД с таймаутами."""
    
    def __init__(self, max_workers: int = 5):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def execute_db_operation(
        self, 
        operation: Callable, 
        *args, 
        operation_name: str = "операция с БД",
        fallback_value: Any = None,
        **kwargs
    ) -> Any:
        """
        Выполняет синхронную операцию с БД в отдельном потоке с таймаутом.
        
        Args:
            operation: Синхронная функция для выполнения
            *args: Аргументы для функции
            operation_name: Название операции для логирования
            fallback_value: Значение по умолчанию при ошибке
            **kwargs: Именованные аргументы для функции
            
        Returns:
            Результат операции или fallback_value при ошибке
        """
        try:
            # Выполняем синхронную операцию в отдельном потоке
            loop = asyncio.get_event_loop()
            result = await with_timeout(
                loop.run_in_executor(self.executor, operation, *args, **kwargs),
                timeout_seconds=DATABASE_TIMEOUT,
                operation_name=operation_name,
                fallback_value=fallback_value
            )
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка в {operation_name}: {e}")
            return fallback_value
    
    def close(self):
        """Закрывает пул потоков."""
        self.executor.shutdown(wait=True)

# Глобальный экземпляр менеджера
db_timeout_manager = DatabaseTimeoutManager()

# Удобные функции для частых операций
async def safe_db_query(query_func: Callable, *args, **kwargs) -> Any:
    """Безопасное выполнение SQL запроса с таймаутом."""
    return await db_timeout_manager.execute_db_operation(
        query_func, 
        *args, 
        operation_name="SQL запрос",
        fallback_value=None,
        **kwargs
    )

async def safe_db_insert(insert_func: Callable, *args, **kwargs) -> Any:
    """Безопасное выполнение INSERT операции с таймаутом."""
    return await db_timeout_manager.execute_db_operation(
        insert_func, 
        *args, 
        operation_name="INSERT операция",
        fallback_value=False,
        **kwargs
    )

async def safe_db_update(update_func: Callable, *args, **kwargs) -> Any:
    """Безопасное выполнение UPDATE операции с таймаутом."""
    return await db_timeout_manager.execute_db_operation(
        update_func, 
        *args, 
        operation_name="UPDATE операция",
        fallback_value=False,
        **kwargs
    )

async def safe_db_delete(delete_func: Callable, *args, **kwargs) -> Any:
    """Безопасное выполнение DELETE операции с таймаутом."""
    return await db_timeout_manager.execute_db_operation(
        delete_func, 
        *args, 
        operation_name="DELETE операция",
        fallback_value=False,
        **kwargs
    )

