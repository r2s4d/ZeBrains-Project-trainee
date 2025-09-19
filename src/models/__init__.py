# Импортируем необходимые модули
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
# Это нужно для безопасного хранения паролей и настроек
load_dotenv()

# Импортируем все модели из файла database.py
from src.models.database import Base, Source, News, NewsSource, Curator, Expert, Summary, Comment, Post, DigestSession, BotSession

# Импортируем централизованную конфигурацию
from src.config import config

# Создаем строку подключения к базе данных из централизованной конфигурации
# Формат: postgresql://пользователь:пароль@хост:порт/название_базы
DATABASE_URL = f"postgresql://{config.database.user}:{config.database.password}@{config.database.host}:{config.database.port}/{config.database.name}"

# Создаем движок базы данных (engine)
# Это основной объект для работы с базой данных
engine = create_engine(
    DATABASE_URL,
    echo=True,  # Показывать SQL-запросы в консоли (полезно для отладки)
    pool_size=5,  # Количество соединений в пуле
    max_overflow=10  # Максимальное количество дополнительных соединений
)

# Создаем фабрику сессий
# Сессия - это объект для выполнения операций с базой данных
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Функция для получения сессии базы данных
def get_db():
    """
    Функция для получения сессии базы данных.
    Используется в контекстном менеджере (with) для автоматического закрытия соединения.
    """
    db = SessionLocal()
    try:
        yield db  # Возвращаем сессию
    finally:
        db.close()  # Закрываем сессию в любом случае

# Функция для создания всех таблиц в базе данных
def create_tables():
    """
    Создает все таблицы в базе данных на основе моделей SQLAlchemy.
    Вызывается один раз при первом запуске приложения.
    """
    Base.metadata.create_all(bind=engine)
    print("✅ Все таблицы успешно созданы в базе данных!")

# Функция для удаления всех таблиц (осторожно!)
def drop_tables():
    """
    Удаляет все таблицы из базы данных.
    ВНИМАНИЕ: Используйте только для разработки, данные будут потеряны!
    """
    Base.metadata.drop_all(bind=engine)
    print("🗑️ Все таблицы удалены из базы данных!")

# Пояснения:
# - load_dotenv() - загружает переменные из файла .env (пароли, настройки)
# - create_engine() - создает подключение к базе данных
# - SessionLocal - фабрика для создания сессий
# - get_db() - функция для безопасного получения сессии
# - create_tables() - создает таблицы в базе данных
# - drop_tables() - удаляет таблицы (только для разработки)
