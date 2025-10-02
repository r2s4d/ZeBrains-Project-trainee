"""
Сервис для работы с реальной базой данных PostgreSQL.
Заменит mock DatabaseService на реальные SQL запросы.
"""

from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from datetime import datetime
import logging
import hashlib

from src.models.database import Source, News, Expert, Comment, NewsSource
from src.services.sqlite_cache_service import cache, get_cache_key

# Настройка логирования
logger = logging.getLogger(__name__)

class PostgreSQLDatabaseService:
    """Сервис для работы с реальной PostgreSQL базой данных."""
    
    def __init__(self):
        """Инициализация сервиса."""
        self.engine = None
        self.SessionLocal = None
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
            # Создаем ключ кэша
            cache_key = get_cache_key("db_approved_news", limit)
            
            # Проверяем кэш
            cached_news = cache.get(cache_key)
            if cached_news:
                logger.info(f"🎯 Одобренные новости из кэша: {len(cached_news)} новостей")
                return cached_news
            
            with self.get_session() as session:
                # Получаем одобренные новости, отсортированные по дате
                news_list = session.query(News).filter(
                    News.status == "approved"
                ).order_by(News.created_at.desc()).limit(limit).all()
                
                logger.info(f"📊 Получено {len(news_list)} одобренных новостей для дайджеста")
                
                # Конвертируем в словари для кэширования
                news_dicts = []
                for news in news_list:
                    news_dict = {
                        'id': news.id,
                        'title': news.title,
                        'content': news.content,
                        'status': news.status,
                        'created_at': news.created_at.isoformat() if news.created_at else None,
                        'published_at': news.published_at.isoformat() if news.published_at else None
                    }
                    news_dicts.append(news_dict)
                
                # Сохраняем в кэш на 1 час
                cache.set(cache_key, news_dicts, expire_seconds=3600)
                logger.debug(f"💾 Одобренные новости сохранены в кэш: {cache_key}")
                
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
            # Создаем ключ кэша
            cache_key = get_cache_key("db_expert_of_week", self.selected_expert_id)
            
            # Проверяем кэш
            cached_expert = cache.get(cache_key)
            if cached_expert:
                logger.info(f"🎯 Эксперт недели из кэша: {cached_expert.get('name', 'Unknown')}")
                # Конвертируем обратно в объект Expert
                expert = Expert()
                expert.id = cached_expert['id']
                expert.name = cached_expert['name']
                expert.specialization = cached_expert['specialization']
                expert.is_active = cached_expert['is_active']
                return expert
            
            with self.get_session() as session:
                # Если есть выбранный эксперт в памяти, возвращаем его
                if self.selected_expert_id:
                    expert = session.query(Expert).filter(Expert.id == self.selected_expert_id).first()
                    if expert:
                        logger.info(f"👤 Возвращаем выбранного эксперта недели: {expert.name}")
                        
                        # Сохраняем в кэш на 6 часов
                        expert_dict = {
                            'id': expert.id,
                            'name': expert.name,
                            'specialization': expert.specialization,
                            'is_active': expert.is_active
                        }
                        cache.set(cache_key, expert_dict, expire_seconds=21600)
                        logger.debug(f"💾 Эксперт недели сохранен в кэш: {cache_key}")
                        
                        return expert
                
                # Иначе возвращаем первого активного эксперта
                expert = session.query(Expert).filter(
                    Expert.is_active == True
                ).first()
                
                if expert:
                    logger.info(f"👤 Возвращаем первого активного эксперта: {expert.name}")
                    
                    # Сохраняем в кэш на 6 часов
                    expert_dict = {
                        'id': expert.id,
                        'name': expert.name,
                        'specialization': expert.specialization,
                        'is_active': expert.is_active
                    }
                    cache.set(cache_key, expert_dict, expire_seconds=21600)
                    logger.debug(f"💾 Эксперт недели сохранен в кэш: {cache_key}")
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
    
    async def get_expert_comments_for_news(self, news_ids: List[int]) -> Dict[int, Dict]:
        """
        Получить комментарии экспертов к новостям из bot_sessions.
        
        Args:
            news_ids: Список ID новостей
            
        Returns:
            Dict[int, Dict]: Словарь {news_id: comment_data}
        """
        try:
            from src.services.bot_session_service import bot_session_service
            
            # Получаем все комментарии из bot_sessions
            all_comments = await bot_session_service.get_active_sessions('expert_comment')
            
            # Формируем словарь комментариев для нужных новостей
            comments_dict = {}
            logger.info(f"🔍 Найдено комментариев в БД: {len(all_comments)} для новостей: {news_ids}")
            
            for comment_session in all_comments:
                data = comment_session.get('data', {})
                news_id = data.get('news_id')
                
                if news_id in news_ids:
                    expert_id = data.get('expert_id')
                    
                    # Получаем данные эксперта
                    with self.get_session() as session:
                        expert = session.query(Expert).filter(Expert.telegram_id == str(expert_id)).first()
                        expert_name = expert.name if expert else "Неизвестный эксперт"
                        expert_specialization = expert.specialization if expert else "AI"
                    
                    comments_dict[news_id] = {
                        "text": data.get('comment', ''),
                        "expert": {
                            "name": expert_name,
                            "specialization": expert_specialization
                        }
                    }
                    logger.debug(f"📝 Комментарий для новости {news_id}: {data.get('comment', '')[:50]}...")
            
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
            # Создаем ключ кэша
            news_ids_str = "_".join(map(str, sorted(news_ids)))
            cache_key = get_cache_key("db_news_sources", news_ids_str)
            
            # Проверяем кэш
            cached_sources = cache.get(cache_key)
            if cached_sources:
                logger.info(f"🎯 Источники новостей из кэша: {len(cached_sources)} новостей")
                return cached_sources
            
            with self.get_session() as session:
                # Получаем новости с их источниками
                news_list = session.query(News).filter(
                    News.id.in_(news_ids)
                ).all()
                
                # Формируем словарь источников
                sources_dict = {}
                
                for news in news_list:
                    # Получаем ВСЕ источники через связь NewsSource (приоритет над news.source_url)
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
                        
                        # Создаем ссылки на все уникальные источники (максимум 3)
                        if unique_sources:
                            source_links = []
                            for source in list(unique_sources)[:3]:  # Ограничиваем до 3
                                # Находим соответствующий NewsSource для получения source_url
                                ns = next((ns for ns in news_sources if ns.source_id == source.id), None)
                                
                                if ns and ns.source_url:
                                    # Используем конкретную ссылку на сообщение
                                    source_link = f'<a href="{ns.source_url}">{source.name}</a>'
                                elif source.telegram_id:
                                    # Форматируем как @channel_name с HTML-ссылкой на канал
                                    clean_telegram_id = source.telegram_id.lstrip('@')
                                    source_link = f'<a href="https://t.me/{clean_telegram_id}">{source.name}</a>'
                                else:
                                    source_link = source.name
                                source_links.append(source_link)
                            sources_dict[int(news.id)] = source_links  # Все ссылки на источники
                            logger.debug(f"✅ Новость {news.id}: источники {', '.join(source_links)}")
                        else:
                            sources_dict[int(news.id)] = ["Неизвестный источник"]
                            logger.warning(f"❌ Новость {news.id}: нет источников")
                    else:
                        # Fallback: используем news.source_url если нет связей NewsSource
                        if news.source_url and news.source_channel_username:
                            # Используем HTML-ссылку для красивого отображения @channel
                            channel_name = news.source_channel_username.lstrip('@')
                            source_link = f'<a href="{news.source_url}">@{channel_name}</a>'
                            sources_dict[int(news.id)] = [source_link]
                            logger.debug(f"✅ Новость {news.id}: fallback HTML-ссылка @{channel_name}")
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
                                sources_dict[int(news.id)] = [source_link]  # Одна ссылка на источник
                                logger.debug(f"⚠️ Новость {news.id}: fallback источник {source_link}")
                            else:
                                sources_dict[int(news.id)] = ["Неизвестный источник"]
                                logger.warning(f"❌ Новость {news.id}: нет источников")
                
                logger.info(f"✅ Возвращаем источники для {len(sources_dict)} новостей")
                
                # Сохраняем в кэш на 2 часа
                cache.set(cache_key, sources_dict, expire_seconds=7200)
                logger.debug(f"💾 Источники новостей сохранены в кэш: {cache_key}")
                
                return sources_dict
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения источников: {e}")
            return {}
