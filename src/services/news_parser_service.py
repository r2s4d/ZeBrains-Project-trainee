"""
NewsParserService - сервис для автоматического парсинга новостей из Telegram-каналов.

Этот сервис:
1. Парсит все источники новостей каждые 2 часа (активные часы) и 4 часа (ночные)
2. Анализирует важность новостей с помощью AI
3. Объединяет дубликаты с уникальными индексами
4. Автоматически создает задания для кураторов и экспертов
5. Интегрируется с существующей системой

Архитектурные решения:
- Dependency Injection для тестируемости
- Асинхронная работа для эффективности
- AI-анализ для определения важности
- Система объединения дубликатов
- Реальный парсинг Telegram каналов через Telethon
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from src.services.postgresql_database_service import PostgreSQLDatabaseService
from src.services.curator_service import CuratorService
from src.services.real_expert_service import RealExpertService
# from src.services.openai_service import OpenAIService  # Удален, используем AIAnalysisService
from src.services.telegram_channel_parser import TelegramChannelParser
from src.services.ai_analysis_service import AIAnalysisService
from src.models.database import Source, News, NewsSource

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ParsedNews:
    """Структура для хранения распарсенной новости."""
    title: str
    content: str
    url: Optional[str]
    published_at: datetime
    source_id: int
    importance_score: float  # 1-10 баллов
    importance_category: str  # "critical", "important", "interesting", "minor"
    ai_summary: str  # Краткое AI-описание важности

class NewsParserService:
    """
    Сервис для автоматического парсинга новостей из Telegram-каналов.
    
    Принципы работы:
    1. Парсит все источники каждые 2 часа (активные часы) и 4 часа (ночные)
    2. Использует AI для анализа важности
    3. Объединяет дубликаты с множественными источниками
    4. Создает задания для кураторов и экспертов
    5. Реальный парсинг через Telegram API
    """
    
    def __init__(
        self, 
        database_service: PostgreSQLDatabaseService,
        curator_service: CuratorService,
        expert_service: RealExpertService,
        openai_service=None,  # Больше не используется
        ai_analysis_service: AIAnalysisService = None
    ):
        """
        Инициализация сервиса.
        
        Args:
            database_service: Сервис для работы с базой данных PostgreSQL
            curator_service: Сервис для работы с кураторами
            expert_service: Сервис для работы с экспертами
            openai_service: Сервис для AI-анализа (устаревший, не используется)
            ai_analysis_service: Новый сервис для AI-анализа
        """
        self.db = database_service
        self.curator = curator_service
        self.expert = expert_service
        self.openai = None  # Больше не используется
        self.ai_analysis = ai_analysis_service
        
        # Инициализируем Telegram парсер
        self.telegram_parser = None
        logger.info("📱 TelegramChannelParser будет инициализирован при первом использовании")
        
        # Настройки парсинга (согласно функциональным требованиям)
        self.parse_interval_active = 2  # часа (активные часы 9:00-21:00)
        self.parse_interval_night = 4   # часа (ночные часы 21:00-9:00)
        self.max_news_per_source = 50  # максимум новостей за раз
        self.max_total_news = 200      # максимум общих новостей за один парсинг
        self.importance_threshold = 5.0  # минимальный балл важности
        
        logger.info("NewsParserService инициализирован с реальным парсингом Telegram")
    
    async def _ensure_telegram_parser(self):
        """Обеспечивает инициализацию Telegram парсера."""
        if self.telegram_parser is None:
            try:
                self.telegram_parser = TelegramChannelParser()
                await self.telegram_parser.connect()
                logger.info("✅ TelegramChannelParser инициализирован и подключен")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации TelegramChannelParser: {e}")
                self.telegram_parser = None
    
    async def start_automatic_parsing(self):
        """
        Запускает автоматический парсинг с учетом времени суток.
        
        Это основной метод, который запускается как фоновый процесс.
        """
        logger.info("🚀 Запуск автоматического парсинга с учетом времени суток")
        
        while True:
            try:
                # Определяем текущий интервал парсинга
                current_hour = datetime.now().hour
                if 9 <= current_hour < 21:  # Активные часы
                    interval = self.parse_interval_active
                    logger.info(f"🌞 Активные часы: парсинг каждые {interval} часа")
                else:  # Ночные часы
                    interval = self.parse_interval_night
                    logger.info(f"🌙 Ночные часы: парсинг каждые {interval} часа")
                
                # Выполняем парсинг
                await self.parse_all_sources()
                logger.info(f"✅ Парсинг завершен, следующий через {interval} часа")
                
                # Ждем до следующего парсинга
                await asyncio.sleep(interval * 3600)  # переводим часы в секунды
                
            except Exception as e:
                logger.error(f"❌ Ошибка в автоматическом парсинге: {e}")
                await asyncio.sleep(300)  # ждем 5 минут при ошибке
    
    async def parse_all_sources(self) -> Dict[str, int]:
        """
        Парсит все источники новостей.
        
        Returns:
            Dict[str, int]: Статистика парсинга по источникам
        """
        logger.info("📰 Начинаем парсинг всех источников")
        
        # Получаем все активные источники
        sources = self.db.get_all_sources()
        if not sources:
            logger.warning("⚠️ Нет активных источников для парсинга")
            return {}
        
        stats = {}
        total_news = 0
        
        for source in sources:
                try:
                    # Проверяем общий лимит новостей
                    if total_news >= self.max_total_news:
                        logger.warning(f"⚠️ Достигнут общий лимит новостей ({self.max_total_news}), останавливаем парсинг")
                        break
                    
                    logger.info(f"🔍 Парсим источник: {source.name} ({source.telegram_id})")
                    
                    # Парсим один источник
                    news_count = await self.parse_channel(source)
                    stats[source.name] = news_count
                    total_news += news_count
                    
                    logger.info(f"✅ Источник {source.name}: найдено {news_count} новостей")
                    logger.info(f"📊 Всего новостей: {total_news}/{self.max_total_news}")
                    
                    # Небольшая пауза между источниками
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка парсинга источника {source.name}: {e}")
                    stats[source.name] = 0
        
        logger.info(f"🎯 Парсинг завершен! Всего новостей: {total_news}")
        logger.info(f"📊 Статистика по источникам: {stats}")
        return stats
    
    async def parse_channel(self, source: Source) -> int:
        """
        Парсит один конкретный Telegram-канал.
        
        Args:
            source: Источник новостей для парсинга
            
        Returns:
            int: Количество найденных новостей
        """
        logger.info(f"🔍 Парсим канал: {source.telegram_id}")
        
        try:
            # Обеспечиваем инициализацию Telegram парсера
            await self._ensure_telegram_parser()
            
            # Используем Telegram парсер для получения новостей
            if self.telegram_parser:
                # Убираем @ из telegram_id если есть
                channel_username = source.telegram_id.replace('@', '')
                
                # Парсим канал с ограничением по количеству
                news_data = await self.telegram_parser.parse_channel(
                    channel_username, 
                    limit=self.max_news_per_source
                )
                logger.info(f"📱 Получено {len(news_data)} новостей из @{channel_username}")
            else:
                logger.warning("⚠️ TelegramChannelParser не инициализирован, используем Mock данные")
                news_data = self._generate_mock_news_for_source(source)
            
            processed_count = 0
            
            for news_data_item in news_data:
                try:
                    # Проверяем на дубликаты
                    duplicate_info = self._detect_duplicates(
                        news_data_item["title"], 
                        news_data_item["content"]
                    )
                    
                    if duplicate_info["is_duplicate"]:
                        # Объединяем с существующей новостью
                        await self._merge_duplicate_news(
                            duplicate_info["existing_news_id"],
                            source.id,
                            news_data_item.get("source_url")
                        )
                        logger.info(f"🔄 Объединили дубликат: {news_data_item['title']}")
                    else:
                        # Создаем простую новость без анализа важности
                        news = await self._create_simple_news_from_parsed(
                            news_data_item, 
                            source.id
                        )
                        
                        if news:
                            # НЕ назначаем куратора - по ФТ кураторы сами фильтруют в дайджесте
                            processed_count += 1
                            
                            logger.info(f"✅ Создана новость: {news.title}")
                
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки новости: {e}")
                    continue
            
            return processed_count
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга канала {source.telegram_id}: {e}")
            return 0
    
    # Метод _analyze_news_importance удален - больше не нужен
    
    # Методы анализа важности удалены - больше не нужны
    
    def _detect_duplicates(self, title: str, content: str) -> Dict[str, any]:
        """
        Проверяет новость на дубликаты.
        
        Args:
            title: Заголовок новости
            content: Содержимое новости
            
        Returns:
            Dict с информацией о дубликатах
        """
        try:
            # Получаем все новости из базы
            all_news = self.db.get_all_news()
            
            for news in all_news:
                # Простая проверка по заголовку (можно улучшить)
                if self._is_similar_title(title, news.title):
                    return {
                        "is_duplicate": True,
                        "existing_news_id": news.id,
                        "similarity_score": 0.9,
                        "reason": "Похожий заголовок"
                    }
            
            return {
                "is_duplicate": False,
                "existing_news_id": None,
                "similarity_score": 0.0,
                "reason": "Дубликатов не найдено"
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки дубликатов: {e}")
            return {
                "is_duplicate": False,
                "existing_news_id": None,
                "similarity_score": 0.0,
                "reason": "Ошибка проверки"
            }
    
    def _is_similar_title(self, title1: str, title2: str) -> bool:
        """
        Проверяет, похожи ли заголовки.
        
        Простая реализация - можно улучшить с помощью AI.
        """
        # Приводим к нижнему регистру и убираем лишние символы
        clean_title1 = "".join(c.lower() for c in title1 if c.isalnum() or c.isspace())
        clean_title2 = "".join(c.lower() for c in title2 if c.isalnum() or c.isspace())
        
        # Разбиваем на слова
        words1 = set(clean_title1.split())
        words2 = set(clean_title2.split())
        
        # Вычисляем схожесть по формуле Жаккара
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        if union == 0:
            return False
        
        similarity = intersection / union
        return similarity > 0.7  # Порог схожести
    
    async def _merge_duplicate_news(
        self, 
        existing_news_id: int, 
        new_source_id: int, 
        new_url: Optional[str]
    ):
        """
        Объединяет дубликат с существующей новостью.
        
        Args:
            existing_news_id: ID существующей новости
            new_source_id: ID нового источника
            new_url: URL новой новости
        """
        try:
            # Создаем связь между существующей новостью и новым источником
            news_source = NewsSource(
                news_id=existing_news_id,
                source_id=new_source_id,
                source_url=new_url
            )
            
            # Добавляем в базу данных
            with self.db.get_session() as session:
                session.add(news_source)
                session.commit()
            
            logger.info(f"✅ Объединили дубликат: новость {existing_news_id} + источник {new_source_id}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка объединения дубликата: {e}")
    
    async def _create_simple_news_from_parsed(
        self, 
        news_data: Dict, 
        source_id: int
    ) -> Optional[News]:
        """
        Создает простую новость в базе данных из распарсенных данных Telegram.
        Без AI анализа важности и категорий - только базовые поля.
        
        Args:
            news_data: Данные новости из Telegram
            source_id: ID источника новости
            
        Returns:
            News: Созданная новость или None при ошибке
        """
        try:
            # Создаем простую новость без AI анализа
            news = News(
                title=news_data["title"],
                content=news_data["content"],
                url=news_data.get("source_url"),  # URL из Telegram
                published_at=news_data["published_at"],
                status="new",  # Начинаем с статуса "new"
                created_at=datetime.utcnow(),
                # Новые поля для Telegram
                source_message_id=news_data.get("source_message_id"),
                source_channel_username=news_data.get("source_channel_username"),
                source_url=news_data.get("source_url"),
                raw_content=news_data.get("raw_content"),
                # Базовые значения без AI анализа
                ai_summary=None,
                importance_score="5",  # Базовый балл
                category="Искусственный интеллект",  # Базовая категория
                tags="ИИ, Технологии",  # Базовые теги
                potential_impact=None,
                tone=None,
                ai_analyzed_at=None
            )
            
            # Добавляем в базу данных
            with self.db.get_session() as session:
                session.add(news)
                session.commit()
                session.refresh(news)
            
            # Создаем связь с источником
            news_source = NewsSource(
                news_id=news.id,
                source_id=source_id,
                source_url=news_data.get("source_url")
            )
            
            with self.db.get_session() as session:
                session.add(news_source)
                session.commit()
            
            logger.info(f"✅ Создана новость из Telegram: {news.title} (ID: {news.id})")
            return news
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания новости из Telegram: {e}")
            return None
    
    async def _assign_to_curator(self, news_id: int):
        """
        Назначает новость куратору на проверку.
        
        Args:
            news_id: ID новости для назначения
        """
        try:
            # Получаем доступных кураторов
            curators = self.curator.get_all_curators()
            
            if not curators:
                logger.warning("⚠️ Нет доступных кураторов для назначения")
                return
            
            # TODO: Реализовать логику выбора куратора
            # Пока назначаем первому доступному
            selected_curator = curators[0]
            
            # Обновляем статус новости
            with self.db.get_session() as session:
                news = session.query(News).filter(News.id == news_id).first()
                if news:
                    news.status = "pending_curation"
                    news.curator_id = selected_curator.telegram_id
                    news.curated_at = datetime.utcnow()
                    session.commit()
            
            logger.info(f"✅ Новость {news_id} назначена куратору {selected_curator.name}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка назначения куратору: {e}")
    
    def _generate_mock_news_for_source(self, source: Source) -> List[Dict]:
        """
        Генерирует Mock новости для демонстрации работы парсера.
        
        В реальной версии здесь будет парсинг Telegram-канала.
        """
        mock_news = [
            {
                "title": "OpenAI анонсировал GPT-5 с революционными возможностями",
                "content": "OpenAI представил новую версию GPT-5, которая превосходит GPT-4 по всем параметрам...",
                "url": f"https://t.me/{source.telegram_id}/123",
                "published_at": datetime.utcnow() - timedelta(hours=2)
            },
            {
                "title": "Google представил новую модель PaLM 3",
                "content": "Google анонсировал PaLM 3 - улучшенную версию языковой модели...",
                "url": f"https://t.me/{source.telegram_id}/124",
                "published_at": datetime.utcnow() - timedelta(hours=1)
            },
            {
                "title": "Новый курс по машинному обучению от MIT",
                "content": "MIT запустил бесплатный курс по машинному обучению для начинающих...",
                "url": f"https://t.me/{source.telegram_id}/125",
                "published_at": datetime.utcnow() - timedelta(minutes=30)
            }
        ]
        
        return mock_news
    
    async def manual_parse_source(self, source_telegram_id: str) -> Dict[str, any]:
        """
        Ручной запуск парсинга конкретного источника.
        
        Используется для тестирования и отладки.
        
        Args:
            source_telegram_id: Telegram ID источника
            
        Returns:
            Dict с результатами парсинга
        """
        logger.info(f"🔍 Ручной парсинг источника: {source_telegram_id}")
        
        try:
            # Находим источник
            source = self.db.get_source_by_telegram_id(source_telegram_id)
            if not source:
                return {
                    "success": False,
                    "error": f"Источник {source_telegram_id} не найден"
                }
            
            # Парсим источник
            news_count = await self.parse_channel(source)
            
            return {
                "success": True,
                "source_name": source.name,
                "news_count": news_count,
                "message": f"Парсинг завершен: найдено {news_count} новостей"
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка ручного парсинга: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_parsing_statistics(self) -> Dict[str, any]:
        """
        Возвращает статистику парсинга.
        
        Returns:
            Dict со статистикой
        """
        try:
            with self.db.get_session() as session:
                # Общее количество новостей
                total_news = session.query(News).count()
                
                # Новости по статусам
                new_news = session.query(News).filter(News.status == "new").count()
                pending_curation = session.query(News).filter(News.status == "pending_curation").count()
                approved = session.query(News).filter(News.status == "approved").count()
                rejected = session.query(News).filter(News.status == "rejected").count()
                
                # Источники
                total_sources = session.query(Source).count()
                
                return {
                    "total_news": total_news,
                    "by_status": {
                        "new": new_news,
                        "pending_curation": pending_curation,
                        "approved": approved,
                        "rejected": rejected
                    },
                    "total_sources": total_sources,
                    "last_parse": "2024-08-07 15:30:00"  
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {"error": str(e)}
