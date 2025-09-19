#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scheduler Service for automated tasks.
Handles morning digest sending at 9:00 AM.
"""

import asyncio
import logging
from datetime import datetime, time
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from src.config import config
from src.services.bot_session_service import bot_session_service
from src.services.sqlite_cache_service import cache

logger = logging.getLogger(__name__)

class SchedulerService:
    """
    Сервис планировщика для автоматических задач.
    """
    
    def __init__(self, morning_digest_service, news_parser_service=None):
        """
        Инициализация планировщика.
        
        Args:
            morning_digest_service: Сервис утреннего дайджеста
            news_parser_service: Сервис парсинга новостей
        """
        self.morning_digest_service = morning_digest_service
        self.news_parser_service = news_parser_service
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        
        logger.info("✅ SchedulerService инициализирован")
        if news_parser_service:
            logger.info("📱 Автоматический парсинг новостей будет настроен")
        else:
            logger.warning("⚠️ NewsParserService не передан - автоматический парсинг отключен")
    
    async def start(self):
        """Запускает планировщик."""
        try:
            if not self.is_running:
                # Добавляем задачу отправки дайджеста
                self.scheduler.add_job(
                    func=self._send_morning_digest,
                    trigger=CronTrigger(hour=config.scheduler.morning_digest_hour, minute=config.scheduler.morning_digest_minute),
                    id="morning_digest",
                    name="Отправка утреннего дайджеста",
                    replace_existing=True
                )
                
                # Добавляем автоматический парсинг новостей
                if self.news_parser_service:
                    self.scheduler.add_job(
                        func=self._parse_news_automatically,
                        trigger=CronTrigger(hour=f"{config.scheduler.news_parsing_start_hour}-{config.scheduler.news_parsing_end_hour}", minute=config.scheduler.news_parsing_minute),
                        id="auto_parse_news",
                        name="Автоматический парсинг новостей",
                        replace_existing=True
                    )
                    
                    # Ночной парсинг
                    self.scheduler.add_job(
                        func=self._parse_news_automatically,
                        trigger=CronTrigger(hour=config.scheduler.night_parsing_hours, minute=config.scheduler.night_parsing_minute),
                        id="auto_parse_news_night",
                        name="Ночной парсинг новостей",
                        replace_existing=True
                    )
                    
                    logger.info("📱 Автоматический парсинг новостей настроен:")
                    logger.info("   - Активные часы (9:00-21:00): каждый час")
                    logger.info("   - Ночные часы (21:00-9:00): каждые 4 часа")
                
                # Добавляем задачу очистки кэша каждый час
                self.scheduler.add_job(
                    func=self._cleanup_cache,
                    trigger=CronTrigger(minute=0),  # Каждый час в 0 минут
                    id="cache_cleanup",
                    name="Очистка кэша",
                    replace_existing=True
                )
                
                # Добавляем задачу очистки сессий каждые 30 минут
                self.scheduler.add_job(
                    func=self._cleanup_sessions,
                    trigger=CronTrigger(minute="0,30"),  # Каждые 30 минут
                    id="sessions_cleanup",
                    name="Очистка сессий",
                    replace_existing=True
                )
                
                # Запускаем планировщик
                self.scheduler.start()
                self.is_running = True
                
                logger.info("✅ Планировщик запущен")
                logger.info("📅 Утренний дайджест будет отправляться в 9:00")
                
        except Exception as e:
            logger.error(f"❌ Ошибка запуска планировщика: {e}")
    
    async def stop(self):
        """Останавливает планировщик."""
        try:
            if self.is_running:
                self.scheduler.shutdown()
                self.is_running = False
                logger.info("✅ Планировщик остановлен")
                
        except Exception as e:
            logger.error(f"❌ Ошибка остановки планировщика: {e}")
    
    async def _send_morning_digest(self):
        """
        Автоматически отправляет утренний дайджест в 9:00.
        """
        try:
            logger.info("🌅 Автоматическая отправка утреннего дайджеста...")
            
            # Создаем дайджест
            digest = await self.morning_digest_service.create_morning_digest()
            
            if digest and digest.news_count > 0:
                # Отправляем в чат кураторов
                success = await self.morning_digest_service.send_digest_to_curators_chat_auto(digest)
                
                if success:
                    logger.info(f"✅ Утренний дайджест отправлен автоматически: {digest.news_count} новостей")
                else:
                    logger.error("❌ Ошибка автоматической отправки дайджеста")
            else:
                logger.info("ℹ️ Нет новостей для утреннего дайджеста")
                
        except Exception as e:
            logger.error(f"❌ Ошибка автоматической отправки дайджеста: {e}")
    
    async def _parse_news_automatically(self):
        """
        Автоматически парсит новости из всех источников.
        """
        try:
            if not self.news_parser_service:
                logger.warning("⚠️ NewsParserService недоступен для автоматического парсинга")
                return
                
            logger.info("📱 Запуск автоматического парсинга новостей...")
            
            # Парсим все источники
            result = await self.news_parser_service.parse_all_sources()
            
            if result:
                logger.info(f"✅ Автоматический парсинг завершен: {result.get('total_parsed', 0)} новостей")
            else:
                logger.warning("⚠️ Автоматический парсинг не вернул результатов")
                
        except Exception as e:
            logger.error(f"❌ Ошибка автоматического парсинга новостей: {e}")
    
    async def _cleanup_cache(self):
        """
        Автоматически очищает истекший кэш каждый час.
        """
        try:
            logger.info("🧹 Запуск автоматической очистки кэша...")
            
            # Очищаем истекшие записи
            deleted_count = cache.cleanup_expired()
            
            if deleted_count > 0:
                logger.info(f"✅ Очистка кэша завершена: удалено {deleted_count} истекших записей")
            else:
                logger.info("ℹ️ Очистка кэша: нет истекших записей")
            
            # Получаем статистику кэша
            stats = cache.get_stats()
            logger.info(f"📊 Статистика кэша: {stats['active_entries']} активных записей, {stats['db_size_mb']}MB")
            
        except Exception as e:
            logger.error(f"❌ Ошибка автоматической очистки кэша: {e}")
    
    async def _cleanup_sessions(self):
        """
        Автоматически очищает истекшие сессии каждые 30 минут.
        """
        try:
            logger.info("🧹 Запуск автоматической очистки сессий...")
            
            # Очищаем истекшие сессии
            deleted_count = await bot_session_service.cleanup_expired_sessions()
            
            if deleted_count > 0:
                logger.info(f"✅ Очистка сессий завершена: удалено {deleted_count} истекших сессий")
            else:
                logger.info("ℹ️ Очистка сессий: нет истекших сессий")
            
            # Получаем статистику сессий
            stats = await bot_session_service.get_session_stats()
            logger.info(f"📊 Статистика сессий: {stats.get('active_sessions', 0)} активных, {stats.get('total_sessions', 0)} всего")
            
        except Exception as e:
            logger.error(f"❌ Ошибка автоматической очистки сессий: {e}")
    
    def get_next_run_time(self) -> Optional[datetime]:
        """
        Получает время следующего запуска утреннего дайджеста.
        
        Returns:
            Optional[datetime]: Время следующего запуска или None
        """
        try:
            job = self.scheduler.get_job("morning_digest")
            if job and job.next_run_time:
                return job.next_run_time
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения времени следующего запуска: {e}")
            return None
    
    def get_status(self) -> dict:
        """
        Получает статус планировщика.
        
        Returns:
            dict: Статус планировщика
        """
        try:
            status = {
                "is_running": self.is_running,
                "next_morning_digest": self.get_next_run_time(),
                "jobs_count": len(self.scheduler.get_jobs()),
                "auto_parsing_enabled": self.news_parser_service is not None,
                "cache_stats": cache.get_stats()
            }
            
            # Добавляем информацию о задачах парсинга
            if self.news_parser_service:
                parse_job = self.scheduler.get_job("auto_parse_news")
                night_parse_job = self.scheduler.get_job("auto_parse_news_night")
                
                status.update({
                    "next_parse": parse_job.next_run_time if parse_job else None,
                    "next_night_parse": night_parse_job.next_run_time if night_parse_job else None,
                    "parse_interval_active": "Каждый час (9:00-21:00)",
                    "parse_interval_night": "Каждые 4 часа (21:00-9:00)"
                })
            
            return status
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статуса планировщика: {e}")
            return {"error": str(e)}
