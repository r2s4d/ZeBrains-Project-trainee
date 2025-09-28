"""
Singleton паттерн для PostgreSQLDatabaseService.
Обеспечивает единственный экземпляр подключения к базе данных во всем приложении.
"""

import threading
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class DatabaseServiceSingleton:
    """
    Singleton паттерн для PostgreSQLDatabaseService.
    Гарантирует единственный экземпляр подключения к БД.
    """
    
    _instance: Optional['DatabaseServiceSingleton'] = None
    _service: Optional['PostgreSQLDatabaseService'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Создает единственный экземпляр Singleton."""
        if cls._instance is None:
            with cls._lock:
                # Двойная проверка блокировки
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    logger.info("🔧 Создан новый экземпляр DatabaseServiceSingleton")
        return cls._instance
    
    def get_service(self) -> 'PostgreSQLDatabaseService':
        """
        Возвращает единственный экземпляр PostgreSQLDatabaseService.
        
        Returns:
            PostgreSQLDatabaseService: Единственный экземпляр сервиса БД
        """
        if self._service is None:
            with self._lock:
                # Двойная проверка блокировки
                if self._service is None:
                    from src.services.postgresql_database_service import PostgreSQLDatabaseService
                    self._service = PostgreSQLDatabaseService()
                    logger.info("✅ Создан единственный экземпляр PostgreSQLDatabaseService")
        
        return self._service
    
    def reset_service(self):
        """
        Сбрасывает сервис (для тестирования или переподключения).
        ОСТОРОЖНО: Используйте только при необходимости!
        """
        with self._lock:
            if self._service:
                logger.warning("⚠️ Сброс PostgreSQLDatabaseService singleton")
                # Здесь можно добавить логику закрытия соединений
                self._service = None

# Глобальная функция для получения единственного экземпляра
def get_database_service() -> 'PostgreSQLDatabaseService':
    """
    Получает единственный экземпляр PostgreSQLDatabaseService.
    
    Returns:
        PostgreSQLDatabaseService: Единственный экземпляр сервиса БД
    """
    singleton = DatabaseServiceSingleton()
    return singleton.get_service()

