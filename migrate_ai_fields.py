#!/usr/bin/env python3
"""
Скрипт для миграции базы данных - добавление полей AI анализа.
"""

import os
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def migrate_database():
    """Выполняет миграцию базы данных."""
    try:
        from src.services.postgresql_database_service import PostgreSQLDatabaseService
        
        print("🚀 Начинаем миграцию базы данных...")
        
        # Создаем подключение к базе данных
        db_service = PostgreSQLDatabaseService()
        
        # Проверяем подключение
        from sqlalchemy import text
        with db_service.get_session() as session:
            result = session.execute(text("SELECT 1"))
            print("✅ Подключение к базе данных установлено")
        
        # SQL команды для миграции
        migration_commands = [
            "ALTER TABLE news ADD COLUMN IF NOT EXISTS ai_summary TEXT",
            "ALTER TABLE news ADD COLUMN IF NOT EXISTS importance_score VARCHAR(10)",
            "ALTER TABLE news ADD COLUMN IF NOT EXISTS category VARCHAR(100)",
            "ALTER TABLE news ADD COLUMN IF NOT EXISTS tags TEXT",
            "ALTER TABLE news ADD COLUMN IF NOT EXISTS potential_impact TEXT",
            "ALTER TABLE news ADD COLUMN IF NOT EXISTS tone VARCHAR(20)",
            "ALTER TABLE news ADD COLUMN IF NOT EXISTS ai_analyzed_at TIMESTAMP"
        ]
        
        # Выполняем миграцию
        with db_service.get_session() as session:
            for command in migration_commands:
                try:
                    print(f"🔧 Выполняем: {command}")
                    session.execute(text(command))
                    session.commit()
                    print(f"✅ Успешно: {command}")
                except Exception as e:
                    print(f"⚠️ Предупреждение: {e}")
                    session.rollback()
        
        # Обновляем существующие записи
        print("🔄 Обновляем существующие записи...")
        with db_service.get_session() as session:
            update_command = """
            UPDATE news SET 
                ai_summary = title,
                importance_score = '5.0',
                category = 'Общие технологии ИИ',
                tags = 'ИИ, Технологии',
                potential_impact = 'Может повлиять на развитие технологий ИИ.',
                tone = 'Нейтральная',
                ai_analyzed_at = NOW()
            WHERE ai_summary IS NULL
            """
            
            try:
                result = session.execute(text(update_command))
                session.commit()
                print(f"✅ Обновлено {result.rowcount} записей")
            except Exception as e:
                print(f"⚠️ Ошибка обновления: {e}")
                session.rollback()
        
        # Проверяем результат
        print("📊 Проверяем результат миграции...")
        with db_service.get_session() as session:
            result = session.execute(text("""
                SELECT 
                    COUNT(*) as total_news,
                    COUNT(ai_summary) as with_ai_summary,
                    COUNT(category) as with_category,
                    COUNT(importance_score) as with_importance_score
                FROM news
            """))
            
            stats = result.fetchone()
            print(f"📈 Статистика:")
            print(f"   Всего новостей: {stats[0]}")
            print(f"   С AI саммари: {stats[1]}")
            print(f"   С категорией: {stats[2]}")
            print(f"   С оценкой важности: {stats[3]}")
        
        print("🎉 Миграция завершена успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrate_database()
