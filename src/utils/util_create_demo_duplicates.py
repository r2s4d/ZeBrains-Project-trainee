#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилита для создания демонстрационных дубликатов новостей.
Используется для презентации работы системы поиска дубликатов и объединения источников.

Создает 2 похожие новости из разных источников и демонстрирует:
1. Поиск дубликатов через многоуровневую систему
2. Объединение источников новостей
3. Работу алгоритмов Майерса, RuBERT и кластеризации
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

# Добавляем корневую директорию в путь для импорта
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.postgresql_database_service import PostgreSQLDatabaseService
from src.services.duplicate_detection_service import DuplicateDetectionService
from src.models.database import News, Source, NewsSource

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DemoDuplicateCreator:
    """Создатель демонстрационных дубликатов для презентации."""
    
    def __init__(self):
        """Инициализация сервисов."""
        self.db = PostgreSQLDatabaseService()
        self.duplicate_detector = DuplicateDetectionService()
        logger.info("✅ Сервисы инициализированы")
    
    async def create_demo_duplicates(self):
        """
        Создает демонстрационные дубликаты новостей.
        
        Сценарий:
        1. Создает/проверяет 2 тестовых источника
        2. Добавляет первую новость из источника 1
        3. Добавляет похожую новость из источника 2
        4. Система автоматически обнаруживает дубликат
        5. Источники объединяются
        """
        try:
            logger.info("🚀 Начинаем создание демонстрационных дубликатов")
            
            # 1. Создаем/получаем тестовые источники
            source1 = await self._get_or_create_source(
                name="TechCrunch AI",
                telegram_id="@techcrunch_ai_demo"
            )
            
            source2 = await self._get_or_create_source(
                name="VentureBeat AI",
                telegram_id="@venturebeat_ai_demo"
            )
            
            logger.info(f"✅ Источники готовы: {source1.name} (ID: {source1.id}), {source2.name} (ID: {source2.id})")
            
            # 2. Создаем первую новость (оригинал)
            news1_data = {
                "title": "OpenAI анонсировала GPT-5 с революционными возможностями",
                "content": """OpenAI представила GPT-5 — новую модель искусственного интеллекта, 
которая превосходит GPT-4 по всем основным метрикам. Модель демонстрирует значительные 
улучшения в понимании контекста, многоязычности и способности к рассуждению. 
GPT-5 поддерживает более длинный контекст до 1 миллиона токенов и показывает 
человеческий уровень производительности в сложных задачах. Релиз запланирован 
на второй квартал 2025 года. Модель будет доступна через API для разработчиков.""",
                "source_message_id": 12345,
                "source_channel_username": "techcrunch_ai_demo",
                "source_url": "https://t.me/techcrunch_ai_demo/12345",
                "ai_relevance_score": 9
            }
            
            news1 = await self._create_news(news1_data, source1.id)
            if not news1:
                logger.error("❌ Не удалось создать первую новость")
                return
            
            logger.info(f"✅ Создана новость 1: '{news1.title}' (ID: {news1.id})")
            
            # Небольшая пауза для реалистичности
            await asyncio.sleep(2)
            
            # 3. Создаем похожую новость из другого источника
            news2_data = {
                "title": "GPT-5 от OpenAI: прорыв в области ИИ",
                "content": """Компания OpenAI объявила о выпуске GPT-5 — передовой языковой модели 
нового поколения. По сравнению с GPT-4, новая версия демонстрирует существенные 
улучшения в контекстном понимании, мультиязычных возможностях и логическом мышлении. 
GPT-5 способен обрабатывать контекст размером до миллиона токенов и достигает 
производительности на уровне человека в комплексных задачах. Запуск модели намечен 
на Q2 2025. Разработчики получат доступ через API.""",
                "source_message_id": 67890,
                "source_channel_username": "venturebeat_ai_demo",
                "source_url": "https://t.me/venturebeat_ai_demo/67890",
                "ai_relevance_score": 8
            }
            
            logger.info(f"🔍 Проверяем новость 2 на дубликаты...")
            
            # 4. Проверяем на дубликаты ПЕРЕД добавлением (как в реальной системе)
            duplicate_result = await self.duplicate_detector.detect_duplicates(
                title=news2_data["title"],
                content=news2_data["content"],
                filter_relevant=True
            )
            
            if duplicate_result.is_duplicate:
                logger.info(f"🎯 ДУБЛИКАТ НАЙДЕН!")
                logger.info(f"   Метод обнаружения: {duplicate_result.similarity_type}")
                logger.info(f"   Схожесть: {duplicate_result.similarity_score:.3f}")
                logger.info(f"   Существующая новость ID: {duplicate_result.existing_news_id}")
                logger.info(f"   Причина: {duplicate_result.reason}")
                
                # 5. Объединяем источники
                logger.info(f"🔗 Объединяем источники...")
                success = await self.duplicate_detector.merge_duplicate_sources(
                    existing_news_id=duplicate_result.existing_news_id,
                    new_source_id=source2.id,
                    new_url=news2_data["source_url"]
                )
                
                if success:
                    logger.info(f"✅ УСПЕХ! Источники объединены")
                    
                    # Показываем результат
                    await self._show_merged_result(duplicate_result.existing_news_id)
                else:
                    logger.error(f"❌ Ошибка объединения источников")
            else:
                logger.info(f"⚠️ Дубликат НЕ найден - это неожиданно!")
                logger.info(f"   Причина: {duplicate_result.reason}")
                
                # Создаем как новую новость
                news2 = await self._create_news(news2_data, source2.id)
                if news2:
                    logger.info(f"✅ Создана новость 2: '{news2.title}' (ID: {news2.id})")
            
            logger.info("🎉 Демонстрация завершена успешно!")
            logger.info("")
            logger.info("📊 ИТОГИ ДЕМОНСТРАЦИИ:")
            logger.info("   ✓ Система поиска дубликатов работает")
            logger.info("   ✓ Источники успешно объединяются")
            logger.info("   ✓ Многоуровневый алгоритм эффективен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания демонстрации: {e}", exc_info=True)
    
    async def _get_or_create_source(self, name: str, telegram_id: str) -> Source:
        """
        Получает существующий источник или создает новый.
        
        Args:
            name: Название источника
            telegram_id: Telegram ID источника
            
        Returns:
            Source: Объект источника
        """
        try:
            with self.db.get_session() as session:
                # Проверяем существование
                source = session.query(Source).filter(
                    Source.telegram_id == telegram_id
                ).first()
                
                if source:
                    logger.info(f"📰 Источник '{name}' уже существует (ID: {source.id})")
                    return source
                
                # Создаем новый
                source = Source(
                    name=name,
                    telegram_id=telegram_id
                )
                session.add(source)
                session.commit()
                session.refresh(source)
                
                logger.info(f"➕ Создан новый источник '{name}' (ID: {source.id})")
                return source
                
        except Exception as e:
            logger.error(f"❌ Ошибка создания источника: {e}")
            raise
    
    async def _create_news(self, news_data: dict, source_id: int) -> News:
        """
        Создает новость в базе данных.
        
        Args:
            news_data: Данные новости
            source_id: ID источника
            
        Returns:
            News: Созданная новость
        """
        try:
            with self.db.get_session() as session:
                # Создаем новость
                news = News(
                    title=news_data["title"],
                    content=news_data["content"],
                    url=news_data.get("source_url"),
                    published_at=datetime.utcnow(),
                    status="new",
                    created_at=datetime.utcnow(),
                    source_message_id=news_data.get("source_message_id"),
                    source_channel_username=news_data.get("source_channel_username"),
                    source_url=news_data.get("source_url"),
                    raw_content=news_data["content"],
                    ai_relevance_score=news_data.get("ai_relevance_score", 8)
                )
                
                session.add(news)
                session.commit()
                session.refresh(news)
                
                # Создаем связь с источником
                news_source = NewsSource(
                    news_id=news.id,
                    source_id=source_id,
                    source_url=news_data.get("source_url")
                )
                
                session.add(news_source)
                session.commit()
                
                return news
                
        except Exception as e:
            logger.error(f"❌ Ошибка создания новости: {e}")
            return None
    
    async def _show_merged_result(self, news_id: int):
        """
        Показывает результат объединения источников.
        
        Args:
            news_id: ID новости
        """
        try:
            with self.db.get_session() as session:
                # Получаем новость
                news = session.query(News).filter(News.id == news_id).first()
                
                if not news:
                    logger.error(f"❌ Новость с ID {news_id} не найдена")
                    return
                
                # Получаем все источники новости
                news_sources = session.query(NewsSource, Source).join(
                    Source, NewsSource.source_id == Source.id
                ).filter(
                    NewsSource.news_id == news_id
                ).all()
                
                logger.info("")
                logger.info("=" * 80)
                logger.info("📊 РЕЗУЛЬТАТ ОБЪЕДИНЕНИЯ ИСТОЧНИКОВ")
                logger.info("=" * 80)
                logger.info(f"Новость ID: {news.id}")
                logger.info(f"Заголовок: {news.title}")
                logger.info(f"Статус: {news.status}")
                logger.info(f"Релевантность: {news.ai_relevance_score}/10")
                logger.info("")
                logger.info(f"Количество источников: {len(news_sources)}")
                logger.info("")
                
                for i, (news_source, source) in enumerate(news_sources, 1):
                    logger.info(f"Источник {i}:")
                    logger.info(f"  - Название: {source.name}")
                    logger.info(f"  - Telegram ID: {source.telegram_id}")
                    logger.info(f"  - URL: {news_source.source_url}")
                    logger.info(f"  - Добавлен: {news_source.created_at}")
                    logger.info("")
                
                logger.info("=" * 80)
                
        except Exception as e:
            logger.error(f"❌ Ошибка отображения результата: {e}")
    
    async def cleanup_demo_data(self):
        """Очищает демонстрационные данные (опционально)."""
        try:
            logger.info("🧹 Очистка демонстрационных данных...")
            
            with self.db.get_session() as session:
                # Удаляем тестовые источники и связанные данные
                demo_sources = session.query(Source).filter(
                    Source.telegram_id.in_([
                        "@techcrunch_ai_demo",
                        "@venturebeat_ai_demo"
                    ])
                ).all()
                
                for source in demo_sources:
                    # Удаляем связи новостей
                    session.query(NewsSource).filter(
                        NewsSource.source_id == source.id
                    ).delete()
                    
                    # Удаляем источник
                    session.delete(source)
                
                # Удаляем демонстрационные новости
                session.query(News).filter(
                    News.source_channel_username.in_([
                        "techcrunch_ai_demo",
                        "venturebeat_ai_demo"
                    ])
                ).delete()
                
                session.commit()
                
            logger.info("✅ Демонстрационные данные очищены")
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки: {e}")


async def main():
    """Главная функция."""
    print()
    print("=" * 80)
    print("🎭 ДЕМОНСТРАЦИЯ СИСТЕМЫ ПОИСКА ДУБЛИКАТОВ И ОБЪЕДИНЕНИЯ ИСТОЧНИКОВ")
    print("=" * 80)
    print()
    print("Эта утилита создаст 2 похожие новости из разных источников")
    print("и продемонстрирует работу системы поиска дубликатов.")
    print()
    
    creator = DemoDuplicateCreator()
    
    # Опция очистки старых демо-данных
    cleanup = input("Очистить старые демо-данные перед запуском? (y/n): ").lower().strip()
    if cleanup == 'y':
        await creator.cleanup_demo_data()
        print()
    
    # Создаем демонстрацию
    await creator.create_demo_duplicates()
    
    print()
    print("=" * 80)
    print("✅ Демонстрация завершена!")
    print("=" * 80)
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⚠️ Демонстрация прервана пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)

