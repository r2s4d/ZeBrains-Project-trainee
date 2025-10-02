#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Централизованная конфигурация для AI News Assistant.
Все настройки приложения в одном месте с валидацией.
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Конфигурация базы данных."""
    host: str = "localhost"
    port: int = 5432
    name: str = "ai_news"
    user: str = "postgres"
    password: str = ""
    
    def __post_init__(self):
        """Валидация конфигурации БД."""
        if not self.password:
            logger.warning("⚠️ Пароль БД не установлен")
        if not self.name:
            raise ValueError("Имя базы данных не может быть пустым")


@dataclass
class TelegramConfig:
    """Конфигурация Telegram."""
    # Bot API (для интерактива)
    bot_token: str = ""
    curator_chat_id: str = ""
    channel_id: str = ""
    max_message_length: int = 4096
    max_photo_caption_length: int = 1024
    
    # User API (для публикации) - уровень безопасности 1+2
    api_id: Optional[int] = None
    api_hash: str = ""
    user_session_name: str = "AI_News_Curator"
    
    def __post_init__(self):
        """Валидация конфигурации Telegram."""
        # Bot API обязательные поля
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN не установлен")
        if not self.curator_chat_id:
            raise ValueError("CURATOR_CHAT_ID не установлен")
        if not self.channel_id:
            raise ValueError("CHANNEL_ID не установлен")
        
        # User API предупреждения (не обязательные)
        if not self.api_id or not self.api_hash:
            logger.warning("⚠️ User API не настроен (TELEGRAM_API_ID, TELEGRAM_API_HASH)")
            logger.warning("📋 Публикация будет использовать только Bot API")


@dataclass
class AIConfig:
    """Конфигурация AI сервисов."""
    proxy_api_key: str = ""
    proxy_url: str = "https://openai.api.proxyapi.ru/v1"
    model: str = "openai/gpt-5-mini-2025-08-07"
    max_content_length: int = 1000
    max_analysis_length: int = 3500
    
    def __post_init__(self):
        """Валидация конфигурации AI."""
        if not self.proxy_api_key:
            raise ValueError("PROXY_API_KEY не установлен")


@dataclass
class SecurityConfig:
    """Конфигурация безопасности."""
    ssl_verify: bool = True
    use_https: bool = True
    
    def __post_init__(self):
        """Валидация конфигурации безопасности."""
        if not self.ssl_verify:
            logger.warning("⚠️ SSL верификация отключена - небезопасно!")


@dataclass
class TimeoutConfig:
    """Конфигурация таймаутов."""
    approval_timeout: int = 3600  # 1 час на согласование
    reminder_interval: int = 3600  # 1 час между напоминаниями
    curator_alert_threshold: int = 14400  # 4 часа до уведомления куратора
    news_parsing_interval: int = 1  # 1 час между парсингом новостей
    message_delay_seconds: float = 0.5  # Задержка между сообщениями
    bot_loop_sleep_seconds: int = 1  # Задержка в основном цикле бота
    session_restore_timeout: float = 30.0  # Таймаут восстановления сессий
    
    # Конфигурация для expert_interaction_service
    expert_session_ttl_hours: int = 24  # TTL сессии эксперта в часах
    expert_comment_ttl_hours: int = 2   # TTL комментария эксперта в часах
    
    def __post_init__(self):
        """Валидация конфигурации таймаутов."""
        if self.approval_timeout <= 0:
            raise ValueError("approval_timeout должен быть больше 0")
        if self.reminder_interval <= 0:
            raise ValueError("reminder_interval должен быть больше 0")
        if self.expert_session_ttl_hours <= 0:
            raise ValueError("expert_session_ttl_hours должен быть больше 0")
        if self.expert_comment_ttl_hours <= 0:
            raise ValueError("expert_comment_ttl_hours должен быть больше 0")


@dataclass
class MessageConfig:
    """Конфигурация сообщений."""
    max_digest_length: int = 4096
    max_news_list_length: int = 3500
    max_expert_message_length: int = 3500
    split_message_length: int = 1024
    max_digest_parts: int = 3
    
    def __post_init__(self):
        """Валидация конфигурации сообщений."""
        if self.max_digest_length <= 0:
            raise ValueError("max_digest_length должен быть больше 0")


@dataclass
class SchedulerConfig:
    """Конфигурация планировщика задач."""
    morning_digest_hour: int = 9
    morning_digest_minute: int = 0
    news_parsing_start_hour: int = 9
    news_parsing_end_hour: int = 21
    news_parsing_minute: int = 0
    night_parsing_hours: str = "21-23,0-8"
    night_parsing_minute: int = 0
    
    def __post_init__(self):
        """Валидация конфигурации планировщика."""
        if not (0 <= self.morning_digest_hour <= 23):
            raise ValueError("morning_digest_hour должен быть от 0 до 23")
        if not (0 <= self.morning_digest_minute <= 59):
            raise ValueError("morning_digest_minute должен быть от 0 до 59")


@dataclass
class ExpertConfig:
    """Конфигурация экспертов."""
    test_expert_telegram_id: str = "1326944316"
    test_expert_name: str = "Я (тестовый эксперт)"
    test_expert_specialization: str = "Тестирование"
    
    def __post_init__(self):
        """Валидация конфигурации экспертов."""
        if not self.test_expert_telegram_id:
            raise ValueError("test_expert_telegram_id не может быть пустым")


@dataclass
class DuplicateDetectionConfig:
    """Конфигурация поиска дубликатов новостей."""
    # Временной фильтр
    time_window_hours: int = 24  # Окно поиска дубликатов в часах
    
    # Алгоритм Майерса + Левенштейн
    myers_threshold: float = 0.15  # Порог схожести (15% от длины текста)
    min_text_length: int = 50  # Минимальная длина текста для сравнения
    
    # RuBERT эмбеддинги
    rubert_model: str = "cointegrated/rubert-tiny2"  # Модель для эмбеддингов
    embedding_dimension: int = 312  # Размерность эмбеддингов rubert-tiny2
    cosine_threshold: float = 0.8  # Порог косинусного сходства
    
    # DBSCAN кластеризация
    dbscan_eps: float = 0.3  # Радиус соседства для DBSCAN
    dbscan_min_samples: int = 2  # Минимум образцов в кластере
    
    # Производительность
    max_news_to_compare: int = 50  # Максимум новостей для сравнения
    cache_embeddings: bool = True  # Кэшировать эмбеддинги
    cache_ttl_hours: int = 24  # TTL кэша эмбеддингов в часах
    
    def __post_init__(self):
        """Валидация конфигурации поиска дубликатов."""
        if not (0 < self.myers_threshold < 1):
            raise ValueError("myers_threshold должен быть от 0 до 1")
        if not (0 < self.cosine_threshold < 1):
            raise ValueError("cosine_threshold должен быть от 0 до 1")
        if self.time_window_hours <= 0:
            raise ValueError("time_window_hours должен быть больше 0")
        if self.min_text_length <= 0:
            raise ValueError("min_text_length должен быть больше 0")


@dataclass
class AppConfig:
    """Главная конфигурация приложения."""
    database: DatabaseConfig
    telegram: TelegramConfig
    ai: AIConfig
    security: SecurityConfig
    timeout: TimeoutConfig
    message: MessageConfig
    scheduler: SchedulerConfig
    expert: ExpertConfig
    duplicate_detection: DuplicateDetectionConfig
    
    @classmethod
    def load(cls) -> 'AppConfig':
        """Загружает конфигурацию из переменных окружения."""
        try:
            return cls(
                database=DatabaseConfig(
                    host=os.getenv('DB_HOST', 'localhost'),
                    port=int(os.getenv('DB_PORT', '5432')),
                    name=os.getenv('DB_NAME', 'ai_news_assistant'),
                    user=os.getenv('DB_USER', 'bot_user'),
                    password=os.getenv('DB_PASSWORD', '')
                ),
                telegram=TelegramConfig(
                    # Bot API
                    bot_token=os.getenv('TELEGRAM_BOT_TOKEN', ''),
                    curator_chat_id=os.getenv('CURATOR_CHAT_ID', ''),
                    channel_id=os.getenv('CHANNEL_ID', ''),
                    max_message_length=int(os.getenv('MAX_MESSAGE_LENGTH', '4096')),
                    max_photo_caption_length=int(os.getenv('MAX_PHOTO_CAPTION_LENGTH', '1024')),
                    
                    # User API (безопасность уровня 1+2)
                    api_id=int(os.getenv('TELEGRAM_API_ID', '0')) if os.getenv('TELEGRAM_API_ID') else None,
                    api_hash=os.getenv('TELEGRAM_API_HASH', ''),
                    user_session_name=os.getenv('TELEGRAM_USER_SESSION_NAME', 'AI_News_Curator')
                ),
                ai=AIConfig(
                    proxy_api_key=os.getenv('PROXY_API_KEY', ''),
                    proxy_url=os.getenv('PROXY_URL', 'https://openai.api.proxyapi.ru/v1'),
                    model=os.getenv('AI_MODEL', 'openai/gpt-5-mini-2025-08-07'),
                    max_content_length=int(os.getenv('AI_MAX_CONTENT_LENGTH', '1000')),
                    max_analysis_length=int(os.getenv('AI_MAX_ANALYSIS_LENGTH', '3500'))
                ),
                security=SecurityConfig(
                    ssl_verify=os.getenv('SSL_VERIFY', 'true').lower() == 'true',
                    use_https=os.getenv('USE_HTTPS', 'true').lower() == 'true'
                ),
                timeout=TimeoutConfig(
                    approval_timeout=int(os.getenv('APPROVAL_TIMEOUT', '3600')),
                    reminder_interval=int(os.getenv('REMINDER_INTERVAL', '3600')),
                    curator_alert_threshold=int(os.getenv('CURATOR_ALERT_THRESHOLD', '14400')),
                    news_parsing_interval=int(os.getenv('NEWS_PARSING_INTERVAL', '1')),
                    message_delay_seconds=float(os.getenv('MESSAGE_DELAY_SECONDS', '0.5')),
                    bot_loop_sleep_seconds=int(os.getenv('BOT_LOOP_SLEEP_SECONDS', '1')),
                    session_restore_timeout=float(os.getenv('SESSION_RESTORE_TIMEOUT', '30.0')),
                    expert_session_ttl_hours=int(os.getenv('EXPERT_SESSION_TTL_HOURS', '24')),
                    expert_comment_ttl_hours=int(os.getenv('EXPERT_COMMENT_TTL_HOURS', '2'))
                ),
                message=MessageConfig(
                    max_digest_length=int(os.getenv('MAX_DIGEST_LENGTH', '4096')),
                    max_news_list_length=int(os.getenv('MAX_NEWS_LIST_LENGTH', '3500')),
                    max_expert_message_length=int(os.getenv('MAX_EXPERT_MESSAGE_LENGTH', '3500')),
                    split_message_length=int(os.getenv('SPLIT_MESSAGE_LENGTH', '1024')),
                    max_digest_parts=int(os.getenv('MAX_DIGEST_PARTS', '3'))
                ),
                scheduler=SchedulerConfig(
                    morning_digest_hour=int(os.getenv('MORNING_DIGEST_HOUR', '9')),
                    morning_digest_minute=int(os.getenv('MORNING_DIGEST_MINUTE', '0')),
                    news_parsing_start_hour=int(os.getenv('NEWS_PARSING_START_HOUR', '9')),
                    news_parsing_end_hour=int(os.getenv('NEWS_PARSING_END_HOUR', '21')),
                    news_parsing_minute=int(os.getenv('NEWS_PARSING_MINUTE', '0')),
                    night_parsing_hours=os.getenv('NIGHT_PARSING_HOURS', '21-23,0-8'),
                    night_parsing_minute=int(os.getenv('NIGHT_PARSING_MINUTE', '0'))
                ),
                expert=ExpertConfig(
                    test_expert_telegram_id=os.getenv('TEST_EXPERT_TELEGRAM_ID', '1326944316'),
                    test_expert_name=os.getenv('TEST_EXPERT_NAME', 'Я (тестовый эксперт)'),
                    test_expert_specialization=os.getenv('TEST_EXPERT_SPECIALIZATION', 'Тестирование')
                ),
                duplicate_detection=DuplicateDetectionConfig(
                    time_window_hours=int(os.getenv('DUPLICATE_TIME_WINDOW_HOURS', '24')),
                    myers_threshold=float(os.getenv('DUPLICATE_MYERS_THRESHOLD', '0.15')),
                    min_text_length=int(os.getenv('DUPLICATE_MIN_TEXT_LENGTH', '50')),
                    rubert_model=os.getenv('DUPLICATE_RUBERT_MODEL', 'cointegrated/rubert-tiny2'),
                    embedding_dimension=int(os.getenv('DUPLICATE_EMBEDDING_DIMENSION', '312')),
                    cosine_threshold=float(os.getenv('DUPLICATE_COSINE_THRESHOLD', '0.8')),
                    dbscan_eps=float(os.getenv('DUPLICATE_DBSCAN_EPS', '0.3')),
                    dbscan_min_samples=int(os.getenv('DUPLICATE_DBSCAN_MIN_SAMPLES', '2')),
                    max_news_to_compare=int(os.getenv('DUPLICATE_MAX_NEWS_TO_COMPARE', '50')),
                    cache_embeddings=os.getenv('DUPLICATE_CACHE_EMBEDDINGS', 'true').lower() == 'true',
                    cache_ttl_hours=int(os.getenv('DUPLICATE_CACHE_TTL_HOURS', '24'))
                )
            )
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки конфигурации: {e}")
            raise
    
    def validate(self) -> bool:
        """Валидирует всю конфигурацию."""
        try:
            # Валидация всех подконфигураций
            self.database.__post_init__()
            self.telegram.__post_init__()
            self.ai.__post_init__()
            self.security.__post_init__()
            self.timeout.__post_init__()
            self.message.__post_init__()
            self.scheduler.__post_init__()
            self.expert.__post_init__()
            self.duplicate_detection.__post_init__()
            
            logger.info("✅ Конфигурация успешно валидирована")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка валидации конфигурации: {e}")
            return False


# Глобальный экземпляр конфигурации
config = AppConfig.load()

# Валидируем конфигурацию при импорте
if not config.validate():
    raise RuntimeError("Конфигурация не прошла валидацию")
