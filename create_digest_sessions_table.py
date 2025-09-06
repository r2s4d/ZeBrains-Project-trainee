#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для создания таблицы digest_sessions через PostgreSQLDatabaseService
"""

import os
import sys
import logging
from sqlalchemy import text

# Добавляем путь к модулям
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def create_digest_sessions_table():
    """Создает таблицу digest_sessions через PostgreSQLDatabaseService."""
    
    try:
        # Импортируем сервис базы данных
        from src.services.postgresql_database_service import PostgreSQLDatabaseService
        
        logger.info("🔌 Подключаемся к базе данных через PostgreSQLDatabaseService...")
        
        # Создаем экземпляр сервиса
        db_service = PostgreSQLDatabaseService()
        
        # SQL для создания таблицы
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS digest_sessions (
            id SERIAL PRIMARY KEY,
            chat_id VARCHAR(255) NOT NULL,
            message_ids TEXT NOT NULL,
            news_count INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        );
        """
        
        # SQL для создания индексов
        create_indexes_sql = """
        CREATE INDEX IF NOT EXISTS idx_digest_sessions_chat_id ON digest_sessions(chat_id);
        CREATE INDEX IF NOT EXISTS idx_digest_sessions_is_active ON digest_sessions(is_active);
        CREATE INDEX IF NOT EXISTS idx_digest_sessions_created_at ON digest_sessions(created_at);
        """
        
        logger.info("📄 Создаем таблицу digest_sessions...")
        
        # Выполняем SQL
        with db_service.engine.connect() as connection:
            # Создаем таблицу
            connection.execute(text(create_table_sql))
            
            # Создаем индексы
            connection.execute(text(create_indexes_sql))
            
            # Подтверждаем изменения
            connection.commit()
            
            logger.info("✅ Таблица digest_sessions создана успешно!")
            
            # Проверяем, что таблица создана
            result = connection.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'digest_sessions'
            """))
            
            if result.fetchone():
                logger.info("✅ Таблица digest_sessions найдена в базе данных!")
                
                # Показываем структуру таблицы
                result = connection.execute(text("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = 'digest_sessions'
                    ORDER BY ordinal_position
                """))
                
                logger.info("📋 Структура таблицы digest_sessions:")
                for row in result:
                    logger.info(f"  - {row[0]}: {row[1]} {'(NULL)' if row[2] == 'YES' else '(NOT NULL)'} {f'DEFAULT: {row[3]}' if row[3] else ''}")
                
            else:
                logger.error("❌ Таблица digest_sessions не найдена после создания!")
                
    except Exception as e:
        logger.error(f"❌ Ошибка создания таблицы: {e}")
        import traceback
        logger.error(f"❌ Полный traceback: {traceback.format_exc()}")
        return False
    
    return True

if __name__ == "__main__":
    logger.info("🚀 Создание таблицы digest_sessions...")
    
    if create_digest_sessions_table():
        logger.info("✅ Таблица digest_sessions создана успешно!")
    else:
        logger.error("❌ Создание таблицы завершено с ошибками!")
        sys.exit(1)
