"""
NewsParserService - сервис для автоматического парсинга новостей из Telegram-каналов.

Этот сервис:
1. Парсит все источники новостей каждый час (активные часы) и 4 часа (ночные)
2. Использует DuplicateDetectionService для умного поиска дубликатов
3. Интегрируется с существующей системой

"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from src.services.postgresql_database_service import PostgreSQLDatabaseService
from src.services.telegram_channel_parser import TelegramChannelParser
from src.services.ai_analysis_service import AIAnalysisService
from src.services.duplicate_detection_service import DuplicateDetectionService
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
    ai_summary: str  # Краткое AI-описание важности

class NewsParserService:
    """
    Сервис для автоматического парсинга новостей из Telegram-каналов.
    
    Принципы работы:
    1. Парсит все источники каждый час (днем) и 4 часа (ночью)
    2. Использует AI для анализа важности
    3. Использует DuplicateDetectionService для умного поиска дубликатов
    4. Создает задания для кураторов и экспертов
    5. Реальный парсинг через Telegram API
    """
    
    def __init__(
        self, 
        database_service: PostgreSQLDatabaseService,
        ai_analysis_service: AIAnalysisService = None
    ):
        """
        Инициализация сервиса.
        
        Args:
            database_service: Сервис для работы с базой данных PostgreSQL
            ai_analysis_service: Сервис для AI-анализа
        """
        self.db = database_service
        self.ai_analysis = ai_analysis_service
        self.duplicate_detector = DuplicateDetectionService()
        
        # Инициализируем Telegram парсер
        self.telegram_parser = None
        logger.info("📱 TelegramChannelParser будет инициализирован при первом использовании")
        
        # Настройки парсинга (согласно функциональным требованиям)
        self.parse_interval_active = 1  # часа (активные часы 9:00-21:00)
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
    
    async def is_news_already_processed(
        self, 
        message_id: Optional[int], 
        channel_username: str
    ) -> bool:
        """
        Проверяет, не обрабатывалась ли уже эта новость.
        
        Эта проверка предотвращает повторную обработку одной и той же новости
        при последующих парсингах (например, каждый час).
        
        Args:
            message_id: ID сообщения в Telegram
            channel_username: Username канала (например, '@ai_news')
            
        Returns:
            bool: True если новость уже обработана, False если новая
        """
        # Если message_id не указан - считаем, что новость новая
        if message_id is None:
            return False
        
        try:
            # Нормализуем channel_username (убираем @)
            clean_username = channel_username.replace('@', '')
            
            # Ищем новость с таким же message_id и каналом в БД
            with self.db.get_session() as session:
                existing_news = session.query(News).filter(
                    News.source_message_id == message_id,
                    News.source_channel_username == clean_username
                ).first()
                
                if existing_news:
                    logger.debug(f"⏭️ Новость уже обработана: message_id={message_id}, "
                               f"channel={clean_username}, news_id={existing_news.id}")
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки уникальности новости: {e}")
            # При ошибке считаем новость новой (чтобы не потерять данные)
            return False
    
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
                logger.warning("⚠️ TelegramChannelParser не инициализирован, пропускаем парсинг")
                return 0
            
            processed_count = 0
            
            for news_data_item in news_data:
                try:
                    # 1. СНАЧАЛА проверяем, не обработана ли уже эта новость
                    if await self.is_news_already_processed(
                        news_data_item.get("source_message_id"),
                        source.telegram_id
                    ):
                        logger.info(f"⏭️ Пропускаем уже обработанную новость: "
                                   f"message_id={news_data_item.get('source_message_id')}, "
                                   f"channel={source.telegram_id}")
                        continue
                    
                    # 2. Проверяем релевантность новости через AI
                    title = news_data_item["title"]
                    content = news_data_item["content"]
                    
                    # Проверяем релевантность только если AI сервис доступен
                    is_relevant = True  # По умолчанию считаем релевантной
                    relevance_score = None  # Инициализируем переменную
                    if self.ai_analysis:
                        try:
                            relevance_score = await self.ai_analysis.analyze_news_relevance(title, content)
                            
                            if relevance_score is not None and relevance_score >= 6:
                                is_relevant = True
                                logger.info(f"✅ Новость релевантна: {relevance_score}/10 - '{title[:50]}...'")
                            else:
                                is_relevant = False
                                logger.info(f"❌ Новость нерелевантна: {relevance_score}/10 - '{title[:50]}...'")
                                
                        except Exception as e:
                            logger.warning(f"⚠️ Ошибка AI анализа релевантности: {e}")
                            # При ошибке AI считаем новость релевантной (fallback)
                            is_relevant = True
                            relevance_score = None  # Сбрасываем оценку при ошибке
                            logger.info(f"✅ Новость включена по fallback (ошибка AI): '{title[:50]}...'")
                    
                    # 3. Если новость нерелевантна - пропускаем её
                    if not is_relevant:
                        logger.info(f"⏭️ Пропускаем нерелевантную новость: '{title[:50]}...'")
                        continue
                    
                    # 4. ТОЛЬКО для релевантных новостей проверяем на дубликаты
                    duplicate_result = await self.duplicate_detector.detect_duplicates(
                        title, 
                        content,
                        filter_relevant=True  # Только релевантные новости
                    )
                    
                    if duplicate_result.is_duplicate:
                        # Объединяем с существующей новостью
                        success = await self.duplicate_detector.merge_duplicate_sources(
                            duplicate_result.existing_news_id,
                            source.id,
                            news_data_item.get("source_url")
                        )
                        
                        if success:
                            logger.info(f"🔄 Объединили дубликат: {news_data_item['title']} "
                                      f"(тип: {duplicate_result.similarity_type}, "
                                      f"схожесть: {duplicate_result.similarity_score:.3f})")
                        else:
                            logger.error(f"❌ Ошибка объединения дубликата: {news_data_item['title']}")
                    else:
                        # Создаем новую новость с оценкой релевантности
                        news = await self._create_simple_news_from_parsed(
                            news_data_item, 
                            source.id,
                            relevance_score=relevance_score
                        )
                        
                        if news:
                            processed_count += 1
                            
                            logger.info(f"✅ Создана новость: {news.title}")
                
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки новости: {e}")
                    continue
            
            return processed_count
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга канала {source.telegram_id}: {e}")
            return 0
    
    
    async def _create_simple_news_from_parsed(
        self, 
        news_data: Dict, 
        source_id: int,
        relevance_score: Optional[int] = None
    ) -> Optional[News]:
        """
        Создает простую новость в базе данных из распарсенных данных Telegram.
        
        Args:
            news_data: Данные новости из Telegram
            source_id: ID источника новости
            relevance_score: Оценка релевантности новости (0-10)
            
        Returns:
            News: Созданная новость или None при ошибке
        """
        try:
            # Создаем новость с AI анализом релевантности
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
                # AI анализ
                ai_summary=None,
                ai_relevance_score=relevance_score  # Сохраняем оценку релевантности
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
    
    
    
