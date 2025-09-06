"""
Конфигурация подключения к базе данных PostgreSQL.
"""

import os
from typing import Optional

class DatabaseConfig:
    """Конфигурация для подключения к базе данных."""
    
    # Параметры подключения к PostgreSQL
    HOST = os.getenv('DB_HOST', 'localhost')
    PORT = os.getenv('DB_PORT', '5432')
    DATABASE = os.getenv('DB_NAME', 'ai_news_assistant')
    USERNAME = os.getenv('DB_USER', 'postgres')
    PASSWORD = os.getenv('DB_PASSWORD', '')  # Будет запрашиваться при подключении
    
    @classmethod
    def get_connection_string(cls) -> str:
        """Возвращает строку подключения к базе данных."""
        if cls.PASSWORD:
            return f"postgresql://{cls.USERNAME}:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/{cls.DATABASE}"
        else:
            return f"postgresql://{cls.USERNAME}@{cls.HOST}:{cls.PORT}/{cls.DATABASE}"
    
    @classmethod
    def get_connection_params(cls) -> dict:
        """Возвращает параметры подключения в виде словаря."""
        return {
            'host': cls.HOST,
            'port': cls.PORT,
            'database': cls.DATABASE,
            'user': cls.USERNAME,
            'password': cls.PASSWORD
        }
    
    @classmethod
    def test_connection(cls) -> bool:
        """Тестирует подключение к базе данных."""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=cls.HOST,
                port=cls.PORT,
                database=cls.DATABASE,
                user=cls.USERNAME,
                password=cls.PASSWORD
            )
            conn.close()
            return True
        except Exception as e:
            print(f"❌ Ошибка подключения к базе данных: {e}")
            return False
