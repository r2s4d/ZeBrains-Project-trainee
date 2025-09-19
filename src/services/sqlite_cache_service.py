#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite кэш для AI News Assistant.
Персистентный кэш с данными на диске.
"""

import sqlite3
import json
import time
import logging
import hashlib
import shutil
from typing import Any, Optional, Dict, List
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SQLiteCache:
    """
    Кэш на основе SQLite с TTL (время жизни).
    """
    
    def __init__(self, db_path: str = "cache.db"):
        self.db_path = db_path
        self.max_size_mb = 100  # Максимальный размер кэша в MB
        self._init_database()
        logger.info(f"✅ SQLiteCache инициализирован: {db_path}")
    
    def _init_database(self):
        """Инициализирует базу данных кэша."""
        with sqlite3.connect(self.db_path) as conn:
            # Включаем WAL режим для лучшей производительности
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    created_at REAL NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    last_accessed REAL NOT NULL
                )
            """)
            
            # Создаем индексы для быстрого поиска
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at 
                ON cache(expires_at)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_last_accessed 
                ON cache(last_accessed)
            """)
            
            conn.commit()
    
    def _get_connection(self):
        """Возвращает соединение с базой данных."""
        return sqlite3.connect(self.db_path)
    
    def _is_expired(self, expires_at: float) -> bool:
        """Проверяет, истек ли срок действия записи."""
        return time.time() > expires_at
    
    def _check_cache_size(self):
        """Проверяет размер кэша и очищает при необходимости."""
        try:
            stats = self.get_stats()
            if stats['db_size_mb'] > self.max_size_mb:
                logger.warning(f"⚠️ Размер кэша превышен: {stats['db_size_mb']}MB > {self.max_size_mb}MB")
                self._cleanup_oldest_entries()
        except Exception as e:
            logger.error(f"❌ Ошибка проверки размера кэша: {e}")
    
    def _cleanup_oldest_entries(self):
        """Удаляет самые старые записи для освобождения места."""
        try:
            with self._get_connection() as conn:
                # Удаляем 20% самых старых записей
                cursor = conn.execute("""
                    DELETE FROM cache 
                    WHERE key IN (
                        SELECT key FROM cache 
                        ORDER BY last_accessed ASC 
                        LIMIT (SELECT COUNT(*) / 5 FROM cache)
                    )
                """)
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"🧹 Удалено {deleted_count} старых записей для освобождения места")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка очистки старых записей: {e}")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Получает значение из кэша.
        
        Args:
            key: Ключ для поиска
            
        Returns:
            Значение или None, если не найдено или истекло
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT value, expires_at FROM cache 
                    WHERE key = ?
                """, (key,))
                row = cursor.fetchone()
                
                if row is None:
                    return None
                
                value, expires_at = row
                
                if self._is_expired(expires_at):
                    # Удаляем истекшую запись
                    conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                    conn.commit()
                    logger.debug(f"🗑️ Удалена истекшая запись: {key}")
                    return None
                
                # Обновляем статистику доступа
                conn.execute("""
                    UPDATE cache 
                    SET access_count = access_count + 1, last_accessed = ?
                    WHERE key = ?
                """, (time.time(), key))
                conn.commit()
                
                logger.debug(f"🎯 Получено из кэша: {key}")
                return json.loads(value)
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения из кэша {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, expire_seconds: int = 3600) -> None:
        """
        Сохраняет значение в кэш.
        
        Args:
            key: Ключ для сохранения
            value: Значение для сохранения
            expire_seconds: Время жизни в секундах (по умолчанию 1 час)
        """
        try:
            expires_at = time.time() + expire_seconds
            created_at = time.time()
            value_json = json.dumps(value, ensure_ascii=False)
            
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO cache 
                    (key, value, expires_at, created_at, access_count, last_accessed)
                    VALUES (?, ?, ?, ?, 0, ?)
                """, (key, value_json, expires_at, created_at, time.time()))
                conn.commit()
            
            logger.debug(f"💾 Сохранено в кэш: {key} (TTL: {expire_seconds}s)")
            
            # Проверяем размер кэша
            self._check_cache_size()
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения в кэш {key}: {e}")
    
    def delete(self, key: str) -> bool:
        """
        Удаляет значение из кэша.
        
        Args:
            key: Ключ для удаления
            
        Returns:
            True если удалено, False если не найдено
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.debug(f"🗑️ Удалено из кэша: {key}")
                    return True
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка удаления из кэша {key}: {e}")
            return False
    
    def clear(self) -> None:
        """Очищает весь кэш."""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM cache")
                conn.commit()
            logger.info("🧹 Кэш полностью очищен")
        except Exception as e:
            logger.error(f"❌ Ошибка очистки кэша: {e}")
    
    def cleanup_expired(self) -> int:
        """
        Удаляет все истекшие записи.
        
        Returns:
            Количество удаленных записей
        """
        try:
            current_time = time.time()
            
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    DELETE FROM cache WHERE expires_at < ?
                """, (current_time,))
                conn.commit()
                
                deleted_count = cursor.rowcount
                
                if deleted_count > 0:
                    logger.info(f"🧹 Удалено {deleted_count} истекших записей")
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"❌ Ошибка очистки истекших записей: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику кэша.
        
        Returns:
            Словарь со статистикой
        """
        try:
            with self._get_connection() as conn:
                # Общее количество записей
                cursor = conn.execute("SELECT COUNT(*) FROM cache")
                total_entries = cursor.fetchone()[0]
                
                # Количество истекших записей
                current_time = time.time()
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM cache WHERE expires_at < ?
                """, (current_time,))
                expired_entries = cursor.fetchone()[0]
                
                # Размер базы данных
                db_size = Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
                
                # Самые популярные ключи
                cursor = conn.execute("""
                    SELECT key, access_count FROM cache 
                    ORDER BY access_count DESC 
                    LIMIT 5
                """)
                popular_keys = cursor.fetchall()
                
                return {
                    'total_entries': total_entries,
                    'active_entries': total_entries - expired_entries,
                    'expired_entries': expired_entries,
                    'db_size_bytes': db_size,
                    'db_size_mb': round(db_size / 1024 / 1024, 2),
                    'max_size_mb': self.max_size_mb,
                    'popular_keys': popular_keys
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики кэша: {e}")
            return {
                'total_entries': 0,
                'active_entries': 0,
                'expired_entries': 0,
                'db_size_bytes': 0,
                'db_size_mb': 0,
                'max_size_mb': self.max_size_mb,
                'popular_keys': []
            }
    
    def backup_cache(self) -> bool:
        """
        Создает резервную копию кэша.
        
        Returns:
            True если успешно
        """
        try:
            backup_path = f"{self.db_path}.backup"
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"💾 Резервная копия кэша создана: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка создания резервной копии: {e}")
            return False
    
    def restore_cache(self, backup_path: str) -> bool:
        """
        Восстанавливает кэш из резервной копии.
        
        Args:
            backup_path: Путь к резервной копии
            
        Returns:
            True если успешно
        """
        try:
            if Path(backup_path).exists():
                shutil.copy2(backup_path, self.db_path)
                logger.info(f"🔄 Кэш восстановлен из резервной копии: {backup_path}")
                return True
            else:
                logger.error(f"❌ Резервная копия не найдена: {backup_path}")
                return False
        except Exception as e:
            logger.error(f"❌ Ошибка восстановления кэша: {e}")
            return False

# Глобальный экземпляр кэша
cache = SQLiteCache()

# Утилиты для работы с кэшем
def get_cache_key(prefix: str, *args) -> str:
    """
    Создает ключ кэша из префикса и аргументов.
    
    Args:
        prefix: Префикс ключа (например, 'ai_summary')
        *args: Аргументы для создания уникального ключа
        
    Returns:
        str: Уникальный ключ кэша
    """
    # Объединяем все аргументы в строку
    key_string = "_".join(str(arg) for arg in args)
    
    # Создаем MD5 хэш для короткого ключа
    key_hash = hashlib.md5(key_string.encode()).hexdigest()[:16]
    
    return f"{prefix}_{key_hash}"

def cache_ai_result(func):
    """
    Декоратор для кэширования результатов AI функций.
    
    Args:
        func: Функция для кэширования
        
    Returns:
        Обернутая функция с кэшированием
    """
    def wrapper(*args, **kwargs):
        # Создаем ключ кэша из аргументов функции
        cache_key = get_cache_key(f"ai_{func.__name__}", *args)
        
        # Проверяем кэш
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"🎯 AI результат из кэша: {func.__name__}")
            return cached_result
        
        # Выполняем функцию
        result = func(*args, **kwargs)
        
        # Сохраняем в кэш на 24 часа
        cache.set(cache_key, result, expire_seconds=86400)
        
        return result
    
    return wrapper

def cache_db_result(expire_seconds: int = 3600):
    """
    Декоратор для кэширования результатов БД функций.
    
    Args:
        expire_seconds: Время жизни кэша в секундах
        
    Returns:
        Декоратор
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Создаем ключ кэша из аргументов функции
            cache_key = get_cache_key(f"db_{func.__name__}", *args)
            
            # Проверяем кэш
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"🎯 БД результат из кэша: {func.__name__}")
                return cached_result
            
            # Выполняем функцию
            result = func(*args, **kwargs)
            
            # Сохраняем в кэш
            cache.set(cache_key, result, expire_seconds=expire_seconds)
            
            return result
        
        return wrapper
    return decorator
