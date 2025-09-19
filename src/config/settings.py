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
    bot_token: str = ""
    curator_chat_id: str = ""
    channel_id: str = ""
    max_message_length: int = 4096
    max_photo_caption_length: int = 1024
    
    def __post_init__(self):
        """Валидация конфигурации Telegram."""
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN не установлен")
        if not self.curator_chat_id:
            raise ValueError("CURATOR_CHAT_ID не установлен")
        if not self.channel_id:
            raise ValueError("CHANNEL_ID не установлен")


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
    
    def __post_init__(self):
        """Валидация конфигурации таймаутов."""
        if self.approval_timeout <= 0:
            raise ValueError("approval_timeout должен быть больше 0")
        if self.reminder_interval <= 0:
            raise ValueError("reminder_interval должен быть больше 0")


@dataclass
class MessageConfig:
    """Конфигурация сообщений."""
    max_digest_length: int = 4096
    max_news_list_length: int = 3500
    max_expert_message_length: int = 3500
    split_message_length: int = 1024
    
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
                    bot_token=os.getenv('TELEGRAM_BOT_TOKEN', ''),
                    curator_chat_id=os.getenv('CURATOR_CHAT_ID', ''),
                    channel_id=os.getenv('CHANNEL_ID', ''),
                    max_message_length=int(os.getenv('MAX_MESSAGE_LENGTH', '4096')),
                    max_photo_caption_length=int(os.getenv('MAX_PHOTO_CAPTION_LENGTH', '1024'))
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
                    news_parsing_interval=int(os.getenv('NEWS_PARSING_INTERVAL', '1'))
                ),
                message=MessageConfig(
                    max_digest_length=int(os.getenv('MAX_DIGEST_LENGTH', '4096')),
                    max_news_list_length=int(os.getenv('MAX_NEWS_LIST_LENGTH', '3500')),
                    max_expert_message_length=int(os.getenv('MAX_EXPERT_MESSAGE_LENGTH', '3500')),
                    split_message_length=int(os.getenv('SPLIT_MESSAGE_LENGTH', '1024'))
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
