"""
Сервис для работы с реальной базой данных PostgreSQL.
Заменит mock DatabaseService на реальные SQL запросы.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import logging

from src.models.database import Source, News, Curator, Expert

# Настройка логирования
logger = logging.getLogger(__name__)

class PostgreSQLDatabaseService:
    """Сервис для работы с реальной PostgreSQL базой данных."""
    
    def __init__(self):
        """Инициализация сервиса."""
        self.engine = None
        self.SessionLocal = None
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Инициализирует подключение к PostgreSQL."""
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from src.config.database_config import DatabaseConfig
            
            # Создаем подключение к PostgreSQL
            connection_string = DatabaseConfig.get_connection_string()
            logger.info(f"🔌 Подключение к PostgreSQL: {connection_string}")
            
            self.engine = create_engine(connection_string)
            self.SessionLocal = sessionmaker(bind=self.engine)
            
            # Тестируем подключение
            with self.get_session() as session:
                from sqlalchemy import text
                session.execute(text("SELECT 1"))
                logger.info("✅ Подключение к PostgreSQL успешно установлено")
                
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации PostgreSQL: {e}")
            self.engine = None
            self.SessionLocal = None
    
    def get_session(self) -> Session:
        """Получает сессию PostgreSQL."""
        if not self.SessionLocal:
            raise Exception("PostgreSQL не инициализирован")
        return self.SessionLocal()
    
    def test_connection(self) -> bool:
        """Тестирует подключение к базе данных."""
        try:
            with self.get_session() as db:
                from sqlalchemy import text
                db.execute(text("SELECT 1"))
                logger.info("✅ Подключение к PostgreSQL работает")
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к PostgreSQL: {e}")
            return False
    
    # ===== РАБОТА С ИСТОЧНИКАМИ (Sources) =====
    
    def add_source(self, name: str, telegram_id: str) -> Optional[Source]:
        """
        Добавляет новый источник новостей.
        
        Args:
            name: Название источника
            telegram_id: Telegram ID источника
            
        Returns:
            Source: Созданный источник или None при ошибке
        """
        with self.get_session() as db:
            try:
                source = Source(name=name, telegram_id=telegram_id)
                db.add(source)
                db.commit()
                db.refresh(source)
                logger.info(f"✅ Источник '{name}' добавлен с ID {source.id}")
                return source
            except IntegrityError:
                db.rollback()
                logger.error(f"❌ Источник с telegram_id '{telegram_id}' уже существует!")
                return None
            except Exception as e:
                db.rollback()
                logger.error(f"❌ Ошибка при добавлении источника: {e}")
                return None
    
    def get_all_sources(self) -> List[Source]:
        """
        Получает все источники новостей.
        
        Returns:
            List[Source]: Список всех источников
        """
        with self.get_session() as db:
            try:
                sources = db.query(Source).all()
                logger.info(f"📊 Получено {len(sources)} источников")
                return sources
            except Exception as e:
                logger.error(f"❌ Ошибка при получении источников: {e}")
                return []
    
    def get_source_by_telegram_id(self, telegram_id: str) -> Optional[Source]:
        """
        Получает источник по Telegram ID.
        
        Args:
            telegram_id: Telegram ID источника
            
        Returns:
            Source: Найденный источник или None
        """
        with self.get_session() as db:
            try:
                source = db.query(Source).filter_by(telegram_id=telegram_id).first()
                if source:
                    logger.info(f"🔍 Найден источник: {source.name}")
                else:
                    logger.warning(f"⚠️ Источник с telegram_id '{telegram_id}' не найден")
                return source
            except Exception as e:
                logger.error(f"❌ Ошибка при поиске источника: {e}")
                return None
    
    # ===== РАБОТА С НОВОСТЯМИ (News) =====
    
    def get_all_news(self) -> List[News]:
        """
        Получает все новости.
        
        Returns:
            List[News]: Список всех новостей
        """
        with self.get_session() as db:
            try:
                news_list = db.query(News).all()
                logger.info(f"📊 Получено {len(news_list)} новостей")
                return news_list
            except Exception as e:
                logger.error(f"❌ Ошибка при получении всех новостей: {e}")
                return []
    
    def get_news_by_id(self, news_id: int) -> Optional[News]:
        """
        Получает новость по ID.
        
        Args:
            news_id: ID новости
            
        Returns:
            News: Найденная новость или None
        """
        with self.get_session() as db:
            try:
                news = db.query(News).filter_by(id=news_id).first()
                return news
            except Exception as e:
                logger.error(f"❌ Ошибка при поиске новости по ID: {e}")
                return None
    
    def get_news_by_status(self, status: str) -> List[News]:
        """
        Получает новости по статусу.
        
        Args:
            status: Статус новости ('new', 'processed', 'approved', 'rejected')
            
        Returns:
            List[News]: Список новостей с указанным статусом
        """
        with self.get_session() as db:
            try:
                news_list = db.query(News).filter_by(status=status).all()
                logger.info(f"📊 Получено {len(news_list)} новостей со статусом '{status}'")
                return news_list
            except Exception as e:
                logger.error(f"❌ Ошибка при получении новостей: {e}")
                return []
    
    def update_news_status(self, news_id: int, new_status: str, curator_id: str = None) -> bool:
        """
        Обновляет статус новости.
        
        Args:
            news_id: ID новости
            new_status: Новый статус
            curator_id: ID куратора (опционально)
            
        Returns:
            bool: True если обновление успешно
        """
        with self.get_session() as db:
            try:
                news = db.query(News).filter_by(id=news_id).first()
                if news:
                    news.status = new_status
                    if curator_id:
                        news.curator_id = curator_id
                        news.curated_at = datetime.utcnow()
                    db.commit()
                    logger.info(f"✅ Статус новости {news_id} обновлен на '{new_status}'")
                    return True
                else:
                    logger.warning(f"⚠️ Новость с ID {news_id} не найдена")
                    return False
            except Exception as e:
                db.rollback()
                logger.error(f"❌ Ошибка обновления статуса новости: {e}")
                return False
    
    # ===== РАБОТА С КУРАТОРАМИ (Curators) =====
    
    def get_all_curators(self) -> List[Curator]:
        """
        Получает всех кураторов.
        
        Returns:
            List[Curator]: Список всех кураторов
        """
        with self.get_session() as db:
            try:
                curators = db.query(Curator).filter_by(is_active=True).all()
                logger.info(f"📊 Получено {len(curators)} активных кураторов")
                return curators
            except Exception as e:
                logger.error(f"❌ Ошибка при получении кураторов: {e}")
                return []
    
    def get_curator_by_id(self, curator_id: int) -> Optional[Curator]:
        """
        Получает куратора по ID.
        
        Args:
            curator_id: ID куратора
            
        Returns:
            Curator: Найденный куратор или None
        """
        with self.get_session() as db:
            try:
                curator = db.query(Curator).filter_by(id=curator_id).first()
                return curator
            except Exception as e:
                logger.error(f"❌ Ошибка при поиске куратора по ID: {e}")
                return None
    
    # ===== РАБОТА С ЭКСПЕРТАМИ (Experts) =====
    
    def get_all_experts(self) -> List[Expert]:
        """
        Получает всех экспертов.
        
        Returns:
            List[Expert]: Список всех экспертов
        """
        with self.get_session() as db:
            try:
                experts = db.query(Expert).filter_by(is_active=True).all()
                logger.info(f"📊 Получено {len(experts)} активных экспертов")
                return experts
            except Exception as e:
                logger.error(f"❌ Ошибка при получении экспертов: {e}")
                return []
    
    def get_expert_by_id(self, expert_id: int) -> Optional[Expert]:
        """
        Получает эксперта по ID.
        
        Args:
            expert_id: ID эксперта
            
        Returns:
            Expert: Найденный эксперт или None
        """
        with self.get_session() as db:
            try:
                expert = db.query(Expert).filter_by(id=expert_id).first()
                return expert
            except Exception as e:
                logger.error(f"❌ Ошибка при поиске эксперта по ID: {e}")
                return None
    
    # ===== СТАТИСТИКА =====
    
    def get_database_stats(self) -> dict:
        """
        Получает статистику базы данных.
        
        Returns:
            dict: Словарь со статистикой
        """
        try:
            with self.get_session() as db:
                stats = {
                    'sources': db.query(Source).count(),
                    'news': db.query(News).count(),
                    'curators': db.query(Curator).filter_by(is_active=True).count(),
                    'experts': db.query(Expert).filter_by(is_active=True).count()
                }
                
                # Статистика по статусам новостей
                status_stats = {}
                for status in ['new', 'processed', 'approved', 'rejected']:
                    status_stats[status] = db.query(News).filter_by(status=status).count()
                stats['news_by_status'] = status_stats
                
                logger.info(f"📊 Статистика БД получена: {stats}")
                return stats
                
        except Exception as e:
            logger.error(f"❌ Ошибка при получении статистики: {e}")
            return {}

    async def get_news_since(self, start_time: datetime) -> List[News]:
        """Получить новости, опубликованные после указанного времени."""
        try:
            with self.get_session() as db:
                news_list = db.query(News).filter(News.published_at >= start_time).all()
                logger.info(f"📊 Получено {len(news_list)} новостей с {start_time}")
                return news_list
        except Exception as e:
            logger.error(f"❌ Ошибка получения новостей с {start_time}: {e}")
            return []
