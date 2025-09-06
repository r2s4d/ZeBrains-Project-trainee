#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для применения миграции: создание таблицы digest_sessions
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text

# Добавляем путь к модулям
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def apply_migration():
    """Применяет миграцию для создания таблицы digest_sessions."""
    
    try:
        # Загружаем переменные окружения
        from dotenv import load_dotenv
        load_dotenv()
        
        # Получаем параметры подключения к БД
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'ai_news_assistant')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', '')
        
        # Создаем строку подключения
        database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        logger.info(f"🔌 Подключаемся к базе данных: {db_host}:{db_port}/{db_name}")
        
        # Создаем подключение к БД
        engine = create_engine(database_url)
        
        # Проверяем подключение
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            logger.info(f"✅ Подключение к PostgreSQL успешно: {version}")
            
            # Читаем SQL миграцию
            migration_file = "migrations/create_digest_sessions_table.sql"
            with open(migration_file, 'r', encoding='utf-8') as f:
                migration_sql = f.read()
            
            logger.info(f"📄 Применяем миграцию: {migration_file}")
            
            # Выполняем миграцию
            connection.execute(text(migration_sql))
            connection.commit()
            
            logger.info("✅ Миграция применена успешно!")
            
            # Проверяем, что таблица создана
            result = connection.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'digest_sessions'
            """))
            
            if result.fetchone():
                logger.info("✅ Таблица digest_sessions создана успешно!")
                
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
                logger.error("❌ Таблица digest_sessions не найдена после миграции!")
                
    except Exception as e:
        logger.error(f"❌ Ошибка применения миграции: {e}")
        import traceback
        logger.error(f"❌ Полный traceback: {traceback.format_exc()}")
        return False
    
    return True

if __name__ == "__main__":
    logger.info("🚀 Запуск миграции digest_sessions...")
    
    if apply_migration():
        logger.info("✅ Миграция завершена успешно!")
    else:
        logger.error("❌ Миграция завершена с ошибками!")
        sys.exit(1)
