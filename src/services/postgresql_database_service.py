"""
Сервис для работы с реальной базой данных PostgreSQL.
Заменит mock DatabaseService на реальные SQL запросы.
"""

from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from src.models.database import Source, News, Expert, Comment, NewsSource

# Настройка логирования
logger = logging.getLogger(__name__)

class PostgreSQLDatabaseService:
    """Сервис для работы с реальной PostgreSQL базой данных."""
    
    def __init__(self):
        """Инициализация сервиса."""
        self.engine = None
        self.SessionLocal = None
        # Временное хранение выбранного эксперта недели
        self.selected_expert_id = None
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
    
    
    # ===== РАБОТА С ИСТОЧНИКАМИ (Sources) =====
    
    
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
    
    # ===== МЕТОДЫ ДЛЯ ФИНАЛЬНОГО ДАЙДЖЕСТА =====
    
    def get_approved_news_for_digest(self, limit: int = 5) -> List[News]:
        """
        Получить одобренные новости для создания дайджеста.
        
        Args:
            limit: Максимальное количество новостей
            
        Returns:
            List[News]: Список одобренных новостей
        """
        try:
            with self.get_session() as session:
                # Получаем одобренные новости, отсортированные по дате
                news_list = session.query(News).filter(
                    News.status == "approved"
                ).order_by(News.created_at.desc()).limit(limit).all()
                
                logger.info(f"📊 Получено {len(news_list)} одобренных новостей для дайджеста")
                return news_list
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения одобренных новостей: {e}")
            return []
    
    def get_expert_of_week(self) -> Optional[Expert]:
        """
        Получить эксперта недели.
        
        Returns:
            Expert: Эксперт недели или None
        """
        try:
            with self.get_session() as session:
                # Если есть выбранный эксперт в памяти, возвращаем его
                if self.selected_expert_id:
                    expert = session.query(Expert).filter(Expert.id == self.selected_expert_id).first()
                    if expert:
                        logger.info(f"👤 Возвращаем выбранного эксперта недели: {expert.name}")
                        return expert
                
                # Иначе возвращаем первого активного эксперта
                expert = session.query(Expert).filter(
                    Expert.is_active == True
                ).first()
                
                if expert:
                    logger.info(f"👤 Возвращаем первого активного эксперта: {expert.name}")
                else:
                    logger.warning("⚠️ Нет активных экспертов")
                
                return expert
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения эксперта недели: {e}")
            return None
    
    def set_expert_of_week(self, expert_id: int) -> bool:
        """
        Установить эксперта недели.
        
        Args:
            expert_id: ID эксперта
            
        Returns:
            bool: True если успешно
        """
        try:
            with self.get_session() as session:
                # Проверяем, что эксперт существует
                expert = session.query(Expert).filter(Expert.id == expert_id).first()
                if expert:
                    # Сохраняем выбранного эксперта в памяти
                    self.selected_expert_id = expert_id
                    
                    logger.info(f"✅ Эксперт недели установлен в памяти: {expert.name} (ID: {expert.id})")
                    return True
                else:
                    logger.error(f"❌ Эксперт с ID {expert_id} не найден")
                    return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка установки эксперта недели: {e}")
            return False
    
    def get_expert_comments_for_news(self, news_ids: List[int]) -> Dict[int, Dict]:
        """
        Получить комментарии экспертов к новостям.
        
        Args:
            news_ids: Список ID новостей
            
        Returns:
            Dict[int, Dict]: Словарь {news_id: comment_data}
        """
        try:
            with self.get_session() as session:
                # Получаем комментарии к новостям
                comments = session.query(Comment).filter(
                    Comment.news_id.in_(news_ids)
                ).all()
                
                # Формируем словарь комментариев
                comments_dict = {}
                logger.info(f"🔍 Найдено комментариев: {len(comments)} для новостей: {news_ids}")
                
                for comment in comments:
                    comments_dict[comment.news_id] = {
                        "text": comment.text,
                        "expert": {
                            "name": comment.expert.name if comment.expert else "Неизвестный эксперт",
                            "specialization": comment.expert.specialization if comment.expert else "AI"
                        }
                    }
                    logger.debug(f"📝 Комментарий для новости {comment.news_id}: {comment.text[:50]}...")
                
                logger.info(f"✅ Возвращаем {len(comments_dict)} комментариев")
                return comments_dict
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения комментариев: {e}")
            return {}
    
    def get_news_sources(self, news_ids: List[int]) -> Dict[int, List[str]]:
        """
        Получить источники новостей.
        
        Args:
            news_ids: Список ID новостей
            
        Returns:
            Dict[int, List[str]]: Словарь {news_id: [source_names]}
        """
        try:
            with self.get_session() as session:
                # Получаем новости с их источниками
                news_list = session.query(News).filter(
                    News.id.in_(news_ids)
                ).all()
                
                # Формируем словарь источников
                sources_dict = {}
                
                for news in news_list:
                    # Получаем источники через связь NewsSource
                    news_sources = session.query(NewsSource).filter(
                        NewsSource.news_id == news.id
                    ).all()
                    
                    logger.debug(f"🔍 Новость {news.id}: найдено {len(news_sources)} связей NewsSource")
                    
                    if news_sources:
                        # Получаем уникальные источники (убираем дубликаты)
                        unique_sources = set()
                        for ns in news_sources:
                            source = session.query(Source).filter(Source.id == ns.source_id).first()
                            if source:
                                unique_sources.add(source)
                        
                        # Создаем одну ссылку на источник (первый уникальный)
                        if unique_sources:
                            source = list(unique_sources)[0]  # Берем первый уникальный источник
                            if source.telegram_id:
                                # Создаем ссылку на Telegram канал
                                if source.telegram_id.startswith('@'):
                                    source_link = f"[{source.name}](https://t.me/{source.telegram_id[1:]})"
                                else:
                                    source_link = f"[{source.name}](https://t.me/{source.telegram_id})"
                            else:
                                source_link = source.name
                            sources_dict[news.id] = [source_link]  # Одна ссылка на источник
                            logger.debug(f"✅ Новость {news.id}: источник {source_link}")
                        else:
                            sources_dict[news.id] = ["Неизвестный источник"]
                            logger.warning(f"❌ Новость {news.id}: нет источников")
                    else:
                        # Fallback для тестовых данных - используем разные источники для разных новостей
                        all_sources = session.query(Source).all()
                        if all_sources:
                            # Используем разные источники для разных новостей
                            source_index = news.id % len(all_sources)
                            source = all_sources[source_index]
                            if source.telegram_id:
                                # Создаем ссылку на Telegram канал
                                if source.telegram_id.startswith('@'):
                                    source_link = f"[{source.name}](https://t.me/{source.telegram_id[1:]})"
                                else:
                                    source_link = f"[{source.name}](https://t.me/{source.telegram_id})"
                            else:
                                source_link = source.name
                            sources_dict[news.id] = [source_link]  # Одна ссылка на источник
                            logger.debug(f"⚠️ Новость {news.id}: fallback источник {source_link}")
                        else:
                            sources_dict[news.id] = ["Неизвестный источник"]
                            logger.warning(f"❌ Новость {news.id}: нет источников")
                
                logger.info(f"✅ Возвращаем источники для {len(sources_dict)} новостей")
                return sources_dict
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения источников: {e}")
            return {}
