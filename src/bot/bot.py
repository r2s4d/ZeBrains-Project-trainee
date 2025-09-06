#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram бот для AI News Assistant.
Интегрирован с BotDatabaseService и OpenAIService для работы с базой данных и AI.
"""

import os
import sys
import logging
import asyncio
from typing import List, Optional, Dict
from datetime import datetime

# Добавляем путь к модулям
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

from src.services.bot_database_service import BotDatabaseService
# from src.services.openai_service import OpenAIService  # Удален, используем AIAnalysisService
from src.services.curator_service import CuratorService
from src.services.post_formatter_service import PostFormatterService
from src.services.real_expert_service import RealExpertService
from src.services.news_parser_service import NewsParserService
from src.services.notification_service import NotificationService
from src.services.publication_service import PublicationService
from src.services.interactive_moderation_service import InteractiveModerationService
from src.services.expert_choice_service import ExpertChoiceService
from src.services.expert_interaction_service import ExpertInteractionService
from src.services.morning_digest_service import MorningDigest
from src.services.final_digest_formatter_service import FinalDigestFormatterService
from src.services.curator_approval_service import CuratorApprovalService
from src.models.database import Source, News, Curator, Expert


# ==================== НАСТРОЙКА ЛОГИРОВАНИЯ ====================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ==================== КЛАСС БОТА ====================

class AINewsBot:
    """
    Telegram бот для управления AI News Assistant.
    Интегрирован с BotDatabaseService и OpenAIService для работы с базой данных и AI.
    """
    
    def __init__(self, token: str):
        """
        Инициализация бота.
        
        Args:
            token (str): Токен Telegram бота
        """
        self.token = token
        self.application = Application.builder().token(token).build()
        self.service = BotDatabaseService()
        
        # Состояние ожидания правок дайджеста
        self.waiting_for_digest_edit = {}  # user_id -> True
        
        # Состояние ожидания фото для публикации
        self.waiting_for_photo = {}  # user_id -> digest_text
        
        # OpenAI сервис больше не нужен, используем AIAnalysisService
        self.ai_service = None
        logger.info("ℹ️ OpenAI сервис отключен, используем AIAnalysisService с ProxyAPI")
        
        self.curator_service = CuratorService(self.service)
        self.post_formatter = PostFormatterService()
        
        # Инициализируем RealExpertService для работы с реальными экспертами
        self.expert_service = RealExpertService(self.service)
        logger.info("✅ RealExpertService подключен для работы с экспертами")
        
        # Инициализируем NewsParserService для автоматического парсинга новостей
        from src.services.postgresql_database_service import PostgreSQLDatabaseService
        from src.services.ai_analysis_service import AIAnalysisService
        
        postgres_db = PostgreSQLDatabaseService()
        
        # Создаем AI сервис для анализа новостей
        try:
            self.ai_analysis_service = AIAnalysisService()
            logger.info("✅ AIAnalysisService подключен для анализа новостей")
        except Exception as e:
            logger.error(f"❌ Ошибка создания AIAnalysisService: {e}")
            # Создаем заглушку
            self.ai_analysis_service = None
        
        self.parser_service = NewsParserService(
            database_service=postgres_db,
            curator_service=self.curator_service,
            expert_service=self.expert_service,
            openai_service=None,  # Больше не используем
            ai_analysis_service=self.ai_analysis_service
        )
        logger.info("✅ NewsParserService подключен для автоматического парсинга с PostgreSQL")
        
        # Инициализируем NotificationService для отправки уведомлений
        self.notification_service = NotificationService(self.service)
        logger.info("✅ NotificationService подключен для отправки уведомлений")
        
        # Инициализируем PublicationService для публикации в канал
        # Токен берём из переменной окружения, чтобы избежать хардкода
        bot_token_env = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token_env:
            bot_token_env = "8195833718:AAGbqnbZz7NrbOWN5ic5k7oxGMUTntgHE6s"
        channel_id = "@egor4ik1234"   # ID вашего канала
        self.publication_service = PublicationService(self.service, bot_token_env, channel_id)
        logger.info("✅ PublicationService подключен для публикации в канал")
        
        
        
        
        # Инициализируем SchedulerService для автоматических задач
        try:
            logger.info("🔧 Начинаем инициализацию SchedulerService...")
            
            from src.services.scheduler_service import SchedulerService
            from src.services.morning_digest_service import MorningDigestService
            from src.services.expert_selection_service import ExpertSelectionService
            
            logger.info("✅ Модули SchedulerService импортированы")
            
            # Проверяем доступность parser_service
            if self.parser_service:
                logger.info("✅ NewsParserService доступен для SchedulerService")
            else:
                logger.warning("⚠️ NewsParserService недоступен для SchedulerService")
            
            self.morning_digest_service = MorningDigestService(
                database_service=postgres_db,
                ai_analysis_service=self.ai_analysis_service,
                notification_service=self.notification_service,
                curator_service=self.curator_service,
                bot=self.application.bot
            )
            logger.info("✅ MorningDigestService создан")
            
            # Инициализируем новые сервисы для финального форматирования
            if self.ai_analysis_service:
                self.final_digest_formatter = FinalDigestFormatterService(self.ai_analysis_service)
                logger.info("✅ FinalDigestFormatterService создан")
                
                # Получаем токен бота и ID кураторского чата
                bot_token = os.getenv('TELEGRAM_BOT_TOKEN', "8195833718:AAGbqnbZz7NrbOWN5ic5k7oxGMUTntgHE6s")
                curator_chat_id = "-1002983482030"  # ID кураторского чата
                self.curator_chat_id = curator_chat_id  # Сохраняем как атрибут класса
                
                self.curator_approval_service = CuratorApprovalService(
                    bot_token=bot_token,
                    curator_chat_id=curator_chat_id,
                    formatter_service=self.final_digest_formatter,
                    bot_instance=self  # Передаем ссылку на бот
                )
                logger.info("✅ CuratorApprovalService создан")
            else:
                logger.warning("⚠️ AIAnalysisService недоступен, финальное форматирование отключено")
                self.final_digest_formatter = None
                self.curator_approval_service = None
            
            self.expert_selection_service = ExpertSelectionService(
                database_service=postgres_db,
                notification_service=self.notification_service
            )
            logger.info("✅ ExpertSelectionService создан")
            
            # Передаем сервисы в MorningDigestService
            self.morning_digest_service.expert_selection_service = self.expert_selection_service
            logger.info("✅ ExpertSelectionService подключен к MorningDigestService")
            
            # Передаем NewsParserService для автоматического парсинга
            logger.info("🔧 Создаем SchedulerService...")
            self.scheduler_service = SchedulerService(
                morning_digest_service=self.morning_digest_service,
                news_parser_service=self.parser_service
            )
            logger.info("✅ SchedulerService подключен для автоматических задач")
            logger.info("📱 Автоматический парсинг новостей включен")
            
            # Планировщик будет запущен в методе run()
        except Exception as e:
            logger.error(f"❌ Ошибка создания SchedulerService: {e}")
            logger.error(f"❌ Тип ошибки: {type(e).__name__}")
            import traceback
            logger.error(f"❌ Полный traceback: {traceback.format_exc()}")
            self.scheduler_service = None
        
        # Инициализируем новые сервисы для интерактивной модерации
        try:
            self.interactive_moderation_service = InteractiveModerationService()
            self.expert_choice_service = ExpertChoiceService()
            self.expert_interaction_service = ExpertInteractionService(
                self.application.bot, 
                self.curator_approval_service
            )
            logger.info("✅ Сервисы интерактивной модерации подключены")
        except Exception as e:
            logger.error(f"❌ Ошибка создания сервисов модерации: {e}")
            self.interactive_moderation_service = None
            self.expert_choice_service = None
            self.expert_interaction_service = None
        
        # Настройка обработчиков
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Настройка обработчиков команд и сообщений."""
        
        # Основные команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        
        # Команда для утренних дайджестов
        self.application.add_handler(CommandHandler("morning_digest", self.morning_digest_command))
        
        # Команда для парсинга новостей
        self.application.add_handler(CommandHandler("parse_now", self.parse_now_command))
        
        # Команда для создания финального дайджеста
        self.application.add_handler(CommandHandler("create_final_digest", self.create_final_digest_command))
        
        
        # Команды планировщика
        self.application.add_handler(CommandHandler("schedule", self.schedule_command))
        self.application.add_handler(CommandHandler("schedule_status", self.schedule_status_command))
        
        # Обработка inline кнопок
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Обработка текстовых сообщений и фото
        self.application.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, self.handle_message))
    
    # ==================== ОСНОВНЫЕ КОМАНДЫ ====================
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start."""
        user = update.effective_user
        
        welcome_text = f"""
🤖 Добро пожаловать в AI News Assistant!

👋 Привет, {user.first_name}!

📰 Этот бот поможет вам:
• Собирать новости по ИИ из Telegram-каналов
• Создавать саммари с помощью OpenAI
• Анализировать важность новостей
• Получать экспертные комментарии
• Публиковать новости в канале
• Управлять уведомлениями для кураторов и экспертов

🔧 Доступные команды:
/help - Справка по командам
/stats - Статистика системы
/notification_stats - Статистика уведомлений

🚀 Начните с команды /help для получения справки!
        """
        
        await update.message.reply_text(welcome_text)
    
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /help."""
        help_text = """
🤖 <b>AI News Assistant Bot - Справка</b>

<b>📋 Основные команды:</b>
/start - Запуск бота
/help - Показать эту справку

<b>🌅 Дайджесты:</b>
/morning_digest - Создать утренний дайджест
/create_final_digest - Создать финальный дайджест

<b>📊 Парсинг новостей:</b>
/parse_now - Запустить парсинг всех каналов за 24 часа

<b>⏰ Планировщик:</b>
/schedule - Запустить планировщик
/schedule_status - Статус планировщика

<b>🔧 Система:</b>
/proxy_status - Статус ProxyAPI

💡 <i>Используйте кнопки для навигации по функциям бота.</i>
        """
        
        await update.message.reply_text(help_text, parse_mode="HTML")
    
    
    
    
    
    
    # ==================== ОБРАБОТКА INLINE КНОПОК ====================
    
    async def _safe_answer_callback(self, query, text: str = None):
        """Безопасно отвечает на callback query с обработкой ошибок."""
        try:
            if text:
                await query.answer(text)
            else:
                await query.answer()
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при ответе на callback query: {e}")
            # Продолжаем выполнение даже если не удалось ответить
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на inline кнопки."""
        query = update.callback_query
        
        # Безопасно отвечаем на callback query с обработкой ошибок
        await self._safe_answer_callback(query)
        
        data = query.data
        logger.info(f"🔘 Обработка callback: {data}")
        
        if data == "admin_stats":
            await self._handle_admin_stats(query)
        elif data == "admin_sources":
            await self._handle_admin_sources(query)
        elif data == "admin_add_source":
            await self._handle_admin_add_source(query)
        elif data == "admin_delete_source":
            await self._handle_admin_delete_source(query)
        elif data == "admin_ai_test":
            await self._handle_admin_ai_test(query)
        elif data == "admin_settings":
            await self._handle_admin_settings(query)
        elif data.startswith("remove_news_"):
            # Обработка удаления новости
            logger.info(f"🗑️ Удаляем новость с ID: {data}")
            news_id = int(data.split("_")[2])
            await self._handle_remove_news(query, query.from_user.id, news_id)
        elif data == "approve_remaining":
            # Обработка одобрения оставшихся новостей
            logger.info(f"✅ Одобряем оставшиеся новости")
            await self._handle_approve_remaining(query, query.from_user.id)
        elif data == "approve_digest":
            # Обработка одобрения финального дайджеста
            logger.info(f"✅ Одобряем финальный дайджест")
            await self._handle_digest_approval(query, query.from_user.id)
        elif data == "edit_digest":
            # Обработка запроса на редактирование дайджеста
            logger.info(f"✏️ Запрос на редактирование дайджеста")
            await self._handle_digest_editing(query, query.from_user.id)
        elif data == "approve_edited_digest":
            # Обработка одобрения исправленного дайджеста
            logger.info(f"✅ Одобряем исправленный дайджест")
            await self._handle_edited_digest_approval(query, query.from_user.id)
        elif data == "edit_digest_again":
            # Обработка повторного редактирования
            logger.info(f"🔄 Повторное редактирование дайджеста")
            await self._handle_digest_editing(query, query.from_user.id)
        elif data.startswith("select_expert_"):
            # Обработка выбора эксперта
            logger.info(f"👨‍💼 Выбираем эксперта: {data}")
            expert_id = int(data.split("_")[2])
            await self._handle_select_expert(query, query.from_user.id, expert_id)
        elif data.startswith("comment_news_"):
            # Обработка запроса на комментирование новости
            logger.info(f"💬 Запрос на комментирование новости: {data}")
            news_id = int(data.split("_")[2])
            await self._handle_comment_request(query, query.from_user.id, news_id)
        else:
            logger.warning(f"❌ Неизвестный callback: {data}")
            await query.edit_message_text("❌ Неизвестная команда")
    
    async def _handle_admin_stats(self, query):
        """Обработка кнопки 'Статистика'."""
        try:
            stats = self.service.get_statistics()
            
            if not stats:
                await query.edit_message_text("❌ Не удалось получить статистику")
                return
            
            # Проверяем статус OpenAI
            ai_status = "🟢 Доступен" if self.ai_analysis_service is not None else "🔴 Недоступен"
            
            stats_text = f"""
📊 Статистика системы

📰 Источники: {stats.get('total_sources', 0)}
📝 Новости: {stats.get('total_news', 0)}
👥 Кураторы: {stats.get('total_curators', 0)}
🧠 Эксперты: {stats.get('total_experts', 0)}
🤖 AI сервис: {ai_status}

🕐 Обновлено: {stats.get('last_update', 'N/A')}
            """
            
            await query.edit_message_text(stats_text)
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            await query.edit_message_text("❌ Ошибка при получении статистики")
    
    async def _handle_admin_sources(self, query):
        """Обработка кнопки 'Источники'."""
        try:
            sources = self.service.get_all_sources()
            
            if not sources:
                await query.edit_message_text("📝 Источники не найдены")
                return
            
            sources_text = "📰 Источники новостей:\n\n"
            
            for i, source in enumerate(sources[:10], 1):  # Показываем первые 10
                sources_text += f"{i}. {source.name} ({source.telegram_id})\n"
            
            if len(sources) > 10:
                sources_text += f"\n... и еще {len(sources) - 10} источников"
            
            await query.edit_message_text(sources_text)
            
        except Exception as e:
            logger.error(f"Ошибка при получении источников: {e}")
            await query.edit_message_text("❌ Ошибка при получении источников")
    
    async def _handle_admin_add_source(self, query):
        """Обработка кнопки 'Добавить источник'."""
        await query.edit_message_text(
            "➕ Добавление источника\n\n"
            "Используйте команду:\n"
            "/add_source <название> <telegram_id>\n\n"
            "Пример:\n"
            "/add_source \"AI News\" @ai_news_channel"
        )
    
    async def _handle_admin_delete_source(self, query):
        """Обработка кнопки 'Удалить источник'."""
        await query.edit_message_text(
            "🗑️ Удаление источника\n\n"
            "Используйте команду:\n"
            "/delete_source <id>\n\n"
            "Сначала посмотрите список источников командой /list_sources"
        )
    
    async def _handle_admin_ai_test(self, query):
        """Обработка кнопки 'AI Тест'."""
        try:
            # Тестируем AI сервис
            test_content = "OpenAI представила новую версию GPT-4"
            summary = self.ai_analysis_service.generate_summary_only(test_content)
            
            if summary:
                result_text = f"""
🤖 Тест AI сервиса

✅ **Саммари сгенерировано:**
{summary[:100]}...

🟢 AI сервис работает корректно
                """
            else:
                result_text = "❌ AI сервис недоступен"
            
            await query.edit_message_text(result_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Ошибка при тестировании AI: {e}")
            await query.edit_message_text("❌ Ошибка при тестировании AI")
    
    async def _handle_admin_settings(self, query):
        """Обработка кнопки 'Настройки'."""
        await query.edit_message_text(
            "⚙️ Настройки системы\n\n"
            "Функция в разработке...\n"
            "Скоро здесь будут настройки бота"
        )
    
    
    
    # ==================== КОМАНДА УТРЕННЕГО ДАЙДЖЕСТА ====================
    
    async def morning_digest_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /morning_digest - создание и отправка утреннего дайджеста."""
        try:
            user = update.effective_user
            logger.info(f"🌅 Команда /morning_digest от пользователя {user.id}")
            
            # Проверяем, является ли пользователь куратором
            if not await self._is_curator(user.id):
                await update.message.reply_text(
                    "❌ У вас нет прав для создания утренних дайджестов.\n"
                    "Эта команда доступна только кураторам."
                )
                return
            
            # Убираем лишнее сообщение - дайджест создается автоматически
            
            # Создаем MorningDigestService
            from src.services.morning_digest_service import MorningDigestService
            
            # Получаем необходимые сервисы
            postgres_db = self._get_postgres_db()
            notification_service = self._get_notification_service()
            curator_service = self._get_curator_service()
            
            # Создаем сервис дайджеста
            digest_service = MorningDigestService(
                database_service=postgres_db,
                ai_analysis_service=self.ai_analysis_service,
                notification_service=notification_service,
                curator_service=curator_service,
                bot=self.application.bot
            )
            
            # Создаем дайджест
            digest = await digest_service.create_morning_digest()
            
            if digest.news_count == 0:
                await update.message.reply_text(
                    "📭 Новостей за последние 24 часа не найдено.\n"
                    "Попробуйте позже или используйте команду /parse_all для парсинга новых новостей."
                )
                return
            
            # Создаем сессию модерации для интерактивного дайджеста
            if hasattr(self, 'interactive_moderation_service') and self.interactive_moderation_service:
                # Создаем сессию модерации
                news_items = [
                    {
                        'id': news.id,
                        'title': news.title,
                        'summary': news.summary,
                        'source_links': news.source_links
                    }
                    for news in digest.news_items
                ]
                
                # Создаем сессию модерации
                self.interactive_moderation_service.create_moderation_session(
                    user_id=user.id,
                    chat_id=update.effective_chat.id,
                    message_id=update.message.message_id,
                    news_items=news_items
                )
            
            # Отправляем дайджест ТОЛЬКО в чат кураторов (по ФТ)
            curators_chat_id = "-1002983482030"  # Реальный ID чата кураторов
            await digest_service.send_digest_to_curators_chat(digest, curators_chat_id)
            
            # Убираем дублирующее сообщение - дайджест уже отправлен в чат кураторов
            
        except Exception as e:
            logger.error(f"❌ Ошибка в morning_digest_command: {e}")
            await update.message.reply_text(
                f"❌ Произошла ошибка при создании дайджеста:\n{str(e)}\n\n"
                "Попробуйте позже или обратитесь к администратору."
            )
    
    async def handle_moderation_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback кнопок модерации."""
        query = update.callback_query
        user = update.effective_user
        
        try:
            # Проверяем права куратора
            if not await self._is_curator(user.id):
                await query.answer("❌ У вас нет прав для модерации!")
                return
            
            callback_data = query.data
            
            if callback_data.startswith("remove_news_"):
                # Удаление новости
                news_id = int(callback_data.split("_")[-1])
                await self._handle_remove_news(query, user.id, news_id)
                
            elif callback_data == "approve_remaining":
                # Одобрение оставшихся новостей
                await self._handle_approve_remaining(query, user.id)
                
            elif callback_data.startswith("select_expert_"):
                # Выбор эксперта
                expert_id = int(callback_data.split("_")[-1])
                await self._handle_select_expert(query, user.id, expert_id)
                
            elif callback_data.startswith("expert_unavailable_"):
                # Эксперт пока недоступен
                await query.answer("⚠️ Этот эксперт пока недоступен для тестирования")
                
            else:
                await query.answer("❌ Неизвестная команда")
                
        except Exception as e:
            logger.error(f"❌ Ошибка в handle_moderation_callback: {e}")
            await query.answer("❌ Произошла ошибка")
    
    async def _handle_remove_news(self, query, user_id: int, news_id: int):
        """Обработка удаления новости."""
        try:
            logger.info(f"🗑️ Удаляем новость {news_id} для пользователя {user_id}")
            
            # Проверяем доступность сервиса модерации
            if not hasattr(self, 'interactive_moderation_service') or not self.interactive_moderation_service:
                logger.error("❌ InteractiveModerationService недоступен")
                await query.answer("❌ Сервис модерации недоступен")
                return
            
            # Удаляем новость из сессии модерации
            success = self.interactive_moderation_service.remove_news_from_session(user_id, news_id)
            if not success:
                await query.answer("❌ Не удалось удалить новость")
                return
            
            # Получаем оставшиеся новости
            remaining_news = self.interactive_moderation_service.get_remaining_news(user_id)
            logger.info(f"📋 Оставшиеся новости: {len(remaining_news)}")
            
            # Очищаем сообщения дайджеста (по JSON-сессии)
            if self.morning_digest_service:
                chat_id_str = str(query.message.chat_id)
                logger.info(f"🔍 Пытаемся очистить сообщения дайджеста для чата: {chat_id_str} (тип: {type(chat_id_str)})")
                
                cleanup_success = await self.morning_digest_service.delete_digest_messages(chat_id_str)
                if cleanup_success:
                    logger.info(f"✅ Сообщения дайджеста очищены для чата {chat_id_str}")
                else:
                    logger.warning(f"⚠️ Не удалось очистить сообщения дайджеста для чата {chat_id_str}")
            
            logger.info(f"🗑️ Результат удаления новости {news_id}: получено {len(remaining_news)} оставшихся новостей")
            
            if remaining_news is not None:
                if remaining_news:
                    # Создаем новый дайджест с оставшимися новостями
                    await self._create_new_digest_after_removal(query, remaining_news)
                else:
                    # Все новости удалены
                    await query.edit_message_text(
                        "📭 Все новости удалены из дайджеста.\n"
                        "Используйте /morning_digest для создания нового дайджеста."
                    )
                
                await query.answer(f"✅ Новость {news_id} удалена, дайджест обновлен")
            else:
                await query.answer("❌ Не удалось удалить новость")
                
        except Exception as e:
            logger.error(f"❌ Ошибка при удалении новости: {e}")
            await query.answer("❌ Произошла ошибка")
    
    async def _handle_select_expert(self, query, user_id: int, expert_id: int):
        """Обработка выбора эксперта."""
        try:
            logger.info(f"👨‍💼 Обрабатываем выбор эксперта {expert_id} для пользователя {user_id}")
            
            if not hasattr(self, 'expert_choice_service') or not self.expert_choice_service:
                logger.error("❌ ExpertChoiceService недоступен")
                await query.answer("❌ Сервис выбора эксперта недоступен")
                return
            
            expert = self.expert_choice_service.get_expert_by_id(expert_id)
            logger.info(f"👨‍💼 Получен эксперт: {expert}")
            
            if not expert:
                logger.error("❌ Эксперт не найден")
                await query.answer("❌ Эксперт не найден")
                return
            
            logger.info(f"👨‍💼 Эксперт найден: {expert.name}, is_test: {expert.is_test}")
            
            if expert.is_test:
                # Сохраняем выбранного эксперта как эксперта недели
                logger.info(f"👨‍💼 Сохраняем эксперта {expert.name} как эксперта недели")
                self.service.set_expert_of_week(expert.id)
                
                # Тестовый эксперт - отправляем новости в личку
                logger.info(f"👨‍💼 Отправляем новости тестовому эксперту {expert.name}")
                await self._send_news_to_expert(query, expert, user_id)
            else:
                logger.info(f"⚠️ Эксперт {expert.name} пока недоступен")
                await query.answer("⚠️ Этот эксперт пока недоступен")
                
        except Exception as e:
            logger.error(f"❌ Ошибка при выборе эксперта: {e}")
            await query.answer("❌ Произошла ошибка")
    
    async def _update_moderation_message(self, query, remaining_news: List[Dict]):
        """Обновляет сообщение с оставшимися новостями."""
        try:
            logger.info(f"📝 Обновляем сообщение модерации, осталось новостей: {len(remaining_news)}")
            
            # Проверяем длину сообщения
            max_length = 4000
            
            # Создаем базовый заголовок
            header = f"""
🌅 <b>УТРЕННИЙ ДАЙДЖЕСТ НОВОСТЕЙ</b>
📰 Осталось новостей: {len(remaining_news)}

<b>📋 НОВОСТИ ДЛЯ МОДЕРАЦИИ:</b>
"""
            
            # Если новостей мало, отправляем как одно сообщение
            if len(remaining_news) <= 5:
                message_text = header
                
                # Добавляем оставшиеся новости
                for i, news in enumerate(remaining_news, 1):
                    message_text += f"""
<b>{i}. {news['title']}</b>
📝 {news['summary']}
➡️ Источник: {news['source_links']}

"""
                
                message_text += """
<b>💡 ИНСТРУКЦИИ:</b>
• Нажмите кнопку "🗑️ Удалить" для каждой ненужной новости
• После удаления ненужных новостей нажмите "✅ Одобрить оставшиеся"
"""
                
                # Создаем кнопки
                buttons = []
                for i, news in enumerate(remaining_news):
                    button_text = f"🗑️ Удалить {i+1}"
                    callback_data = f"remove_news_{news['id']}"
                    logger.info(f"🔘 Создаю кнопку: {button_text} -> {callback_data}")
                    buttons.append([
                        InlineKeyboardButton(
                            button_text, 
                            callback_data=callback_data
                        )
                    ])
                
                # Кнопка одобрения
                approve_button = InlineKeyboardButton(
                    "✅ Одобрить оставшиеся", 
                    callback_data="approve_remaining"
                )
                buttons.append([approve_button])
                
                reply_markup = InlineKeyboardMarkup(buttons)
                
                # Обновляем сообщение
                await query.edit_message_text(
                    text=message_text,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
                logger.info(f"✅ Сообщение модерации обновлено (одно сообщение)")
                
            else:
                # Новостей много, отправляем новое сообщение с разбиением
                await query.edit_message_text(
                    "📝 Обновляем дайджест...",
                    parse_mode="HTML"
                )
                
                # Создаем новый дайджест и отправляем его
                from src.services.morning_digest_service import MorningDigest, DigestNews
                from datetime import datetime
                
                # Создаем объекты DigestNews
                digest_news = []
                for news in remaining_news:
                    digest_item = DigestNews(
                        id=news['id'],
                        title=news['title'],
                        summary=news['summary'],
                        importance_score=news.get('importance_score', 5),
                        category=news.get('category', 'Общие'),
                        source_links=news.get('source_links', ''),
                        published_at=news.get('published_at', datetime.now()),
                        curator_id=news.get('curator_id')
                    )
                    digest_news.append(digest_item)
                
                # Создаем объект дайджеста
                digest = MorningDigest(
                    date=datetime.now(),
                    news_count=len(digest_news),
                    news_items=digest_news,
                    total_importance=5,
                    categories=['Общие'],
                    curator_id=None
                )
                
                # Отправляем новый дайджест через сервис
                success = await self.morning_digest_service.send_digest_to_curators_chat(
                    digest, 
                    str(query.message.chat_id)
                )
                
                if success:
                    logger.info(f"✅ Новый дайджест успешно отправлен после удаления новости")
                else:
                    logger.error(f"❌ Не удалось отправить новый дайджест после удаления новости")

            
        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении сообщения: {e}")
            await query.answer("❌ Ошибка обновления сообщения")
    
    async def _show_expert_choice(self, query, approved_news: List[Dict]):
        """Показывает выбор эксперта."""
        try:
            logger.info(f"👨‍💼 Показываем выбор эксперта для {len(approved_news)} новостей")
            
            if not hasattr(self, 'expert_choice_service') or not self.expert_choice_service:
                logger.error("❌ ExpertChoiceService недоступен")
                await query.edit_message_text("❌ Сервис выбора эксперта недоступен")
                return
            
            message_text = f"""
✅ <b>МОДЕРАЦИЯ ЗАВЕРШЕНА!</b>

📰 Одобрено новостей: {len(approved_news)}
👨‍💻 Выберите эксперта для комментариев:

"""
            
            # Создаем кнопки выбора эксперта
            buttons = self.expert_choice_service.create_expert_choice_buttons()
            logger.info(f"🔘 Создано кнопок выбора эксперта: {len(buttons)}")
            
            reply_markup = InlineKeyboardMarkup(buttons)
            
            # Отправляем новое сообщение вместо редактирования (старое уже удалено)
            await self.application.bot.send_message(
                chat_id=query.message.chat_id,
                text=message_text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            logger.info(f"✅ Сообщение выбора эксперта показано")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при показе выбора эксперта: {e}")
            await query.answer("❌ Ошибка показа выбора эксперта")
    
    async def _send_news_to_expert(self, query, expert, user_id: int):
        """Отправляет одобренные новости эксперту в личку."""
        try:
            logger.info(f"📤 Начинаем отправку новостей эксперту {expert.name} (ID: {expert.id})")
            
            # Проверяем доступность сервисов
            if not hasattr(self, 'interactive_moderation_service') or not self.interactive_moderation_service:
                logger.error("❌ InteractiveModerationService недоступен")
                await query.answer("❌ Сервис модерации недоступен")
                return
            
            if not hasattr(self, 'expert_interaction_service') or not self.expert_interaction_service:
                logger.error("❌ ExpertInteractionService недоступен")
                await query.answer("❌ Сервис взаимодействия с экспертами недоступен")
                return
            
            # Получаем одобренные новости из сессии
            approved_news = self.interactive_moderation_service.get_remaining_news(user_id)
            logger.info(f"📰 Получены одобренные новости: {len(approved_news)} штук")
            
            if not approved_news:
                logger.warning("⚠️ Нет одобренных новостей для отправки")
                await query.answer("❌ Нет одобренных новостей для отправки")
                return
            
            # Определяем ID эксперта для отправки
            if expert.is_test:
                # Для тестового эксперта используем его Telegram ID
                expert_telegram_id = int(expert.telegram_id)
                expert_name = expert.name
                logger.info(f"👨‍💼 Тестовый эксперт: {expert_name}, Telegram ID: {expert_telegram_id}")
            else:
                # Для реальных экспертов пока заглушка
                logger.info(f"⚠️ Реальный эксперт {expert.name} пока не подключен")
                await query.answer("⚠️ Реальные эксперты пока не подключены")
                return
            
            # Отправляем новости эксперту через новый сервис
            logger.info(f"📤 Отправляем {len(approved_news)} новостей эксперту {expert_name}")
            success = await self.expert_interaction_service.send_news_to_expert(
                expert_telegram_id, 
                approved_news, 
                expert_name
            )
            
            if success:
                logger.info(f"✅ Новости успешно отправлены эксперту {expert_name}")
                
                # Очищаем сессию модерации после успешной отправки
                if hasattr(self, 'interactive_moderation_service') and self.interactive_moderation_service:
                    self.interactive_moderation_service.cleanup_moderation_session(user_id)
                    logger.info(f"🧹 Сессия модерации для пользователя {user_id} очищена")
                
                # Обновляем сообщение в чате кураторов
                await query.edit_message_text(
                    text=f"✅ <b>Новости отправлены эксперту!</b>\n\n"
                         f"👨‍💻 <b>Эксперт:</b> {expert.name}\n"
                         f"📰 <b>Количество новостей:</b> {len(approved_news)}\n"
                         f"📤 <b>Статус:</b> Отправлено в личку\n\n"
                         f"⏰ <b>Ожидаем комментарии эксперта...</b>",
                    parse_mode="HTML"
                )
                
                await query.answer(f"✅ Новости отправлены эксперту {expert.name}")
            else:
                logger.error(f"❌ Ошибка отправки новостей эксперту {expert_name}")
                await query.answer("❌ Ошибка отправки новостей эксперту")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке новостей эксперту: {e}")
            await query.answer("❌ Произошла ошибка")
    
    async def _handle_comment_request(self, query, expert_id: int, news_id: int):
        """Обрабатывает запрос эксперта на комментирование новости."""
        try:
            if not hasattr(self, 'expert_interaction_service') or not self.expert_interaction_service:
                await query.answer("❌ Сервис взаимодействия с экспертами недоступен")
                return
            
            # Получаем инструкции для комментирования
            instructions = await self.expert_interaction_service.handle_comment_request(expert_id, news_id)
            
            # Отправляем инструкции эксперту
            await query.message.reply_text(
                text=instructions,
                parse_mode="HTML"
            )
            
            await query.answer("💬 Готовы к комментированию!")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при обработке запроса на комментирование: {e}")
            await query.answer("❌ Произошла ошибка")
    
    # ==================== ОБРАБОТКА СООБЩЕНИЙ ====================
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений."""
        # Проверяем, что update.message существует
        if not update.message:
            logger.warning("⚠️ Получено обновление без сообщения")
            return
            
        user = update.effective_user
        text = update.message.text
        
        # Логируем все входящие сообщения для диагностики
        logger.info(f"📨 Получено сообщение от {user.id}: text={bool(text)}, photo={bool(update.message.photo)}, document={bool(update.message.document)}")
        
        # Проверяем, ожидаем ли мы правки дайджеста от этого пользователя
        if user.id in self.waiting_for_digest_edit:
            logger.info(f"📝 Получены правки дайджеста от пользователя {user.id}")
            await self._handle_digest_edit_message(update, user.id, text)
            return
        
        # Проверяем, ожидаем ли мы фото для публикации от этого пользователя
        logger.info(f"🔍 Проверка фото: user.id={user.id}, waiting_for_photo={list(self.waiting_for_photo.keys())}, has_photo={bool(update.message.photo)}")
        if user.id in self.waiting_for_photo and update.message.photo:
            logger.info(f"📸 Получено фото для публикации от пользователя {user.id}")
            await self._handle_photo_for_publication(update, user.id)
            return
        
        # Проверяем, является ли пользователь экспертом с активной сессией
        if hasattr(self, 'expert_interaction_service') and self.expert_interaction_service:
            # Проверяем, есть ли активная сессия для этого пользователя
            if user.id in self.expert_interaction_service.active_sessions:
                # Это комментарий эксперта - обрабатываем его
                await self._handle_expert_comment(update, user.id, text)
                return
    
    async def _handle_expert_comment(self, update: Update, expert_id: int, comment_text: str):
        """Обрабатывает комментарий эксперта."""
        try:
            if not hasattr(self, 'expert_interaction_service') or not self.expert_interaction_service:
                await update.message.reply_text("❌ Сервис взаимодействия с экспертами недоступен")
                return
            
            # Получаем активную сессию эксперта
            session = self.expert_interaction_service.active_sessions.get(expert_id)
            if not session:
                await update.message.reply_text("❌ Активная сессия не найдена")
                return
            
            # Определяем, к какой новости относится комментарий
            # Берем новость, которую эксперт выбрал для комментирования
            if not hasattr(session, 'selected_news_id') or not session.selected_news_id:
                await update.message.reply_text("❌ Не выбрана новость для комментирования")
                return
            
            news_id = session.selected_news_id
            
            # Проверяем, что новость еще не прокомментирована
            if news_id in session.commented_news:
                await update.message.reply_text("✅ Эта новость уже прокомментирована!")
                return
            
            # Сохраняем комментарий
            success = await self.expert_interaction_service.save_comment(expert_id, news_id, comment_text)
            
            if success:
                # Очищаем выбранную новость
                session.selected_news_id = None
                
                # Если есть еще новости для комментирования, показываем обновленный список
                if len(session.commented_news) < len(session.news_ids):
                    await self._show_updated_expert_news_list(expert_id)
                else:
                    # Все новости прокомментированы - НЕ отправляем сообщение
                    # Эксперт уже получит уведомление от ExpertInteractionService
                    pass
            else:
                await update.message.reply_text("❌ Ошибка сохранения комментария")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки комментария эксперта {expert_id}: {e}")
            await update.message.reply_text("❌ Произошла ошибка при обработке комментария")
    
    async def _show_updated_expert_news_list(self, expert_id: int):
        """Показывает обновленный список новостей для эксперта."""
        try:
            if not hasattr(self, 'expert_interaction_service') or not self.expert_interaction_service:
                return
            
            session = self.expert_interaction_service.active_sessions.get(expert_id)
            if not session:
                return
            
            # Получаем оставшиеся новости
            remaining_news_ids = session.news_ids - session.commented_news
            
            if not remaining_news_ids:
                return
            
            # Получаем реальные данные оставшихся новостей из сессии эксперта
            remaining_news = []
            for news in session.news_items:
                if news['id'] in remaining_news_ids:
                    remaining_news.append(news)
            
            if not remaining_news:
                logger.warning(f"⚠️ Не найдены данные для оставшихся новостей эксперта {expert_id}")
                return
            
            # Отправляем обновленный список (разбитый на части)
            news_parts = self.expert_interaction_service._split_news_list_for_expert(remaining_news)
            
            for i, part in enumerate(news_parts):
                keyboard = self.expert_interaction_service._create_comment_buttons_for_part(part['news_indices'], remaining_news)
                
                await self.expert_interaction_service.bot.send_message(
                    chat_id=expert_id,
                    text=part['text'],
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="HTML"
                )
                
                # Небольшая задержка между сообщениями
                if i < len(news_parts) - 1:
                    await asyncio.sleep(0.5)
            
            logger.info(f"✅ Обновленный список новостей отправлен эксперту {expert_id}: {len(remaining_news)} новостей")
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа обновленного списка новостей эксперту {expert_id}: {e}")
    
    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================
    
    def _get_postgres_db(self):
        """Получает PostgreSQL сервис."""
        try:
            from src.services.postgresql_database_service import PostgreSQLDatabaseService
            return PostgreSQLDatabaseService()
        except Exception as e:
            logger.error(f"❌ Ошибка получения PostgreSQL сервиса: {e}")
            return None
    
    def _get_notification_service(self):
        """Получает сервис уведомлений."""
        try:
            return self.notification_service
        except Exception as e:
            logger.error(f"❌ Ошибка получения NotificationService: {e}")
            return None
    
    def _get_curator_service(self):
        """Получает сервис кураторов."""
        try:
            return self.curator_service
        except Exception as e:
            logger.error(f"❌ Ошибка получения CuratorService: {e}")
            return None
    
    def _get_scheduler_service(self):
        """Получает сервис планировщика."""
        try:
            # Используем уже созданный экземпляр
            if hasattr(self, 'scheduler_service') and self.scheduler_service:
                return self.scheduler_service
            else:
                logger.error("❌ SchedulerService не инициализирован")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения SchedulerService: {e}")
            return None
    
    async def schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /schedule - управление планировщиком."""
        user = update.effective_user
        
        logger.info(f"📅 Команда /schedule от пользователя {user.id}")
        
        try:
            # Проверяем права куратора
            if not await self._is_curator(user.id):
                await update.message.reply_text("❌ У вас нет прав для управления планировщиком!")
                return
            
            # Получаем сервис планировщика
            scheduler_service = self._get_scheduler_service()
            if not scheduler_service:
                await update.message.reply_text("❌ Сервис планировщика недоступен!")
                return
            
            # Запускаем планировщик
            await scheduler_service.start()
            
            # Получаем статус
            status = scheduler_service.get_status()
            next_run = status.get('next_morning_digest')
            
            if next_run:
                next_run_str = next_run.strftime('%d.%m.%Y %H:%M')
            else:
                next_run_str = "Не установлено"
            
            response = f"✅ Планировщик запущен!\n\n"
            response += f"📅 Следующий дайджест: {next_run_str}\n"
            response += f"🕐 Время отправки: 9:00 утра\n"
            response += f"💬 Чат кураторов: ID {scheduler_service.morning_digest_service.curators_chat_id}\n\n"
            response += f"📋 Доступные команды:\n"
            response += f"`schedule_status` - Статус планировщика\n"
            response += f"`morning_digest` - Отправить дайджест сейчас"
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"❌ Ошибка в schedule_command: {e}")
            await update.message.reply_text(f"❌ Ошибка запуска планировщика: {e}")
    
    async def schedule_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /schedule_status - статус планировщика."""
        user = update.effective_user
        
        logger.info(f"📊 Команда /schedule_status от пользователя {user.id}")
        
        try:
            # Проверяем права куратора
            if not await self._is_curator(user.id):
                await update.message.reply_text("❌ У вас нет прав для просмотра статуса планировщика!")
                return
            
            # Получаем сервис планировщика
            scheduler_service = self._get_scheduler_service()
            if not scheduler_service:
                await update.message.reply_text("❌ Сервис планировщика недоступен!")
                return
            
            # Получаем статус
            status = scheduler_service.get_status()
            
            response = f"📊 Статус планировщика\n\n"
            response += f"🔄 Статус: {'✅ Запущен' if status.get('is_running') else '❌ Остановлен'}\n"
            response += f"📅 Следующий дайджест: {status.get('next_morning_digest', 'Не установлено')}\n"
            response += f"📋 Задач в очереди: {status.get('jobs_count', 0)}\n"
            response += f"💬 Чат кураторов: ID {scheduler_service.morning_digest_service.curators_chat_id}\n\n"
            response += f"📋 Доступные команды:\n"
            response += f"`schedule` - Запустить планировщик\n"
            response += f"`morning_digest` - Отправить дайджест сейчас"
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"❌ Ошибка в schedule_status_command: {e}")
            await update.message.reply_text(f"❌ Ошибка получения статуса: {e}")
    
    async def _is_curator(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь куратором."""
        try:
            # Для тестирования считаем всех пользователей кураторами
            # В реальной системе здесь должна быть проверка в базе данных
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка проверки прав куратора: {e}")
            return False
    async def proxy_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает статус ProxyAPI сервиса."""
        try:
            # Получаем статус ProxyAPI через AIAnalysisService
            if hasattr(self, 'ai_analysis_service'):
                status = self.ai_analysis_service.get_proxy_status()
            else:
                status = {
                    "service": "AIAnalysisService",
                    "proxy_available": False,
                    "message": "Сервис AI анализа недоступен"
                }
            
            # Форматируем ответ
            status_text = f"""
🔍 <b>Статус ProxyAPI сервиса</b>

📊 <b>Сервис:</b> {status.get('service', 'Неизвестно')}
🚀 <b>ProxyAPI доступен:</b> {'✅ Да' if status.get('proxy_available') else '❌ Нет'}

"""
            
            if status.get('proxy_available'):
                status_text += f"""
🔗 <b>Прокси URL:</b> <code>{status.get('proxy_url', 'Не указан')}</code>
🔑 <b>ProxyAPI ключ установлен:</b> {'✅ Да' if status.get('proxy_api_key_set') else '❌ Нет'}
🤖 <b>Клиент инициализирован:</b> {'✅ Да' if status.get('client_initialized') else '❌ Нет'}

✅ <b>ProxyAPI работает и будет использован для AI анализа!</b>
"""
            else:
                status_text += f"""
⚠️ <b>ProxyAPI недоступен</b>

📝 <b>Для настройки ProxyAPI:</b>
1. Получите прокси URL от вашего провайдера
2. Добавьте в .env файл:
   PROXY_API_URL=https://your-proxy-domain.com/v1
   PROXY_API_KEY=sk-your-proxy-key
3. Перезапустите бота

ℹ️ <b>Текущий режим:</b> Fallback анализ (без AI)
"""
            
            await update.message.reply_text(status_text, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в proxy_status_command: {e}")
            await update.message.reply_text(
                "❌ Ошибка при получении статуса ProxyAPI. Проверьте логи."
            )
    
    # ==================== ЗАПУСК БОТА ====================
    
    async def run(self):
        """Запуск бота."""
        logger.info("🚀 Запуск AI News Assistant Bot...")
        
        try:
            # Инициализируем и запускаем бота
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            logger.info("✅ Бот успешно запущен!")
            
            # Автоматически запускаем планировщик при старте бота
            logger.info(f"🔍 Проверяем SchedulerService: {self.scheduler_service}")
            
            if self.scheduler_service:
                try:
                    logger.info("🚀 Запускаем планировщик...")
                    await self.scheduler_service.start()
                    logger.info("✅ Планировщик автоматически запущен при старте бота")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось автоматически запустить планировщик: {e}")
                    logger.warning(f"⚠️ Тип ошибки: {type(e).__name__}")
                    import traceback
                    logger.warning(f"⚠️ Полный traceback: {traceback.format_exc()}")
                    logger.info("ℹ️ Планировщик можно запустить вручную командой /schedule")
            else:
                logger.warning("⚠️ SchedulerService недоступен - планировщик не будет работать")
                logger.warning("🔍 Проверьте логи выше для диагностики проблемы")
            
            # Держим бота запущенным
            import asyncio
            while True:
                await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"❌ Ошибка при запуске бота: {e}")
            raise
    
    async def stop(self):
        """Остановка бота."""
        logger.info("🛑 Остановка бота...")
        
        try:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            
            logger.info("✅ Бот успешно остановлен!")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при остановке бота: {e}")
            raise
    
    async def _update_message_fallback(self, query, remaining_news: List[Dict]):
        """
        Fallback метод для обновления сообщения с сокращенным текстом.
        
        Args:
            query: Callback query
            remaining_news: Список оставшихся новостей
        """
        try:
            # Создаем сокращенный текст
            short_text = f"""
🌅 <b>УТРЕННИЙ ДАЙДЖЕСТ НОВОСТЕЙ</b>
📰 Осталось новостей: {len(remaining_news)}

<b>📋 НОВОСТИ ДЛЯ МОДЕРАЦИИ:</b>
"""
            # Добавляем только первые 3 новости для экономии места
            for i, news in enumerate(remaining_news[:3], 1):
                short_text += f"""
<b>{i}. {news['title'][:50]}...</b>
"""
            
            if len(remaining_news) > 3:
                short_text += f"\n... и еще {len(remaining_news) - 3} новостей"
            
            short_text += """
<b>💡 ИНСТРУКЦИИ:</b>
• Нажмите кнопку "🗑️ Удалить" для каждой ненужной новости
• После удаления ненужных новостей нажмите "✅ Одобрить оставшиеся"
"""
            
            # Создаем кнопки только для первых 3 новостей
            buttons = []
            for i, news in enumerate(remaining_news[:3]):
                button_text = f"🗑️ Удалить {i+1}"
                callback_data = f"remove_news_{news['id']}"
                buttons.append([
                    InlineKeyboardButton(
                        button_text, 
                        callback_data=callback_data
                    )
                ])
            
            # Кнопка одобрения
            approve_button = InlineKeyboardButton(
                "✅ Одобрить оставшиеся", 
                callback_data="approve_remaining"
            )
            buttons.append([approve_button])
            
            reply_markup = InlineKeyboardMarkup(buttons)
            
            # Обновляем сообщение
            await query.edit_message_text(
                text=short_text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            logger.info(f"✅ Сообщение обновлено с fallback (сокращенный текст)")
            
        except Exception as fallback_error:
            logger.error(f"❌ Ошибка fallback обновления: {fallback_error}")
            await query.answer("❌ Ошибка обновления дайджеста")
    
    async def _create_new_digest_after_removal(self, query, remaining_news: List[Dict]):
        """
        Создает новый дайджест после удаления новости.
        
        Args:
            query: CallbackQuery от Telegram
            remaining_news: Список оставшихся новостей
        """
        try:
            logger.info(f"🔄 Создаем новый дайджест после удаления новости, осталось: {len(remaining_news)}")
            
            # Создаем объекты DigestNews
            from src.services.morning_digest_service import MorningDigest, DigestNews
            from datetime import datetime
            
            digest_news = []
            for news in remaining_news:
                digest_item = DigestNews(
                    id=news['id'],
                    title=news['title'],
                    summary=news['summary'],
                    importance_score=news.get('importance_score', 5),
                    category=news.get('category', 'Общие'),
                    source_links=news['source_links'],
                    published_at=news.get('published_at', datetime.now()),
                    curator_id=news.get('curator_id')
                )
                digest_news.append(digest_item)
            
            # Создаем объект дайджеста
            digest = MorningDigest(
                date=datetime.now(),
                news_count=len(digest_news),
                news_items=digest_news,
                total_importance=5,
                categories=['Общие']
            )
            
            # Отправляем новый дайджест через сервис
            success = await self.morning_digest_service.send_digest_to_curators_chat(
                digest, 
                str(query.message.chat_id)
            )
            
            if success:
                logger.info(f"✅ Новый дайджест успешно отправлен после удаления новости")
            else:
                logger.error(f"❌ Не удалось отправить новый дайджест после удаления новости")
                
        except Exception as e:
            logger.error(f"❌ Ошибка создания нового дайджеста после удаления: {e}")
    
    async def _force_delete_digest_messages(self, chat_id: str):
        """
        Принудительно удаляет все сообщения дайджеста по содержимому.
        
        Args:
            chat_id: ID чата
        """
        try:
            logger.info(f"🗑️ Принудительно удаляем сообщения дайджеста для чата: {chat_id}")
            
            if not hasattr(self, 'morning_digest_service') or not self.morning_digest_service:
                logger.warning("⚠️ MorningDigestService недоступен")
                return
            
            # Получаем последние сообщения и ищем дайджест
            try:
                # Получаем последние 50 сообщений
                messages = await self.application.bot.get_chat_history(chat_id=int(chat_id), limit=50)
                deleted_count = 0
                
                for msg in messages:
                    if msg.text and any(keyword in msg.text for keyword in ["УТРЕННИЙ ДАЙДЖЕСТ", "НОВОСТИ ДЛЯ МОДЕРАЦИИ", "🗑️ Удалить"]):
                        try:
                            await self.application.bot.delete_message(
                                chat_id=int(chat_id), 
                                message_id=msg.message_id
                            )
                            deleted_count += 1
                            logger.info(f"🗑️ Принудительно удалено сообщение дайджеста: {msg.message_id}")
                            await asyncio.sleep(0.1)  # Небольшая задержка
                        except Exception as e:
                            logger.warning(f"⚠️ Не удалось принудительно удалить сообщение {msg.message_id}: {e}")
                            continue
                
                logger.info(f"✅ Принудительно удалено {deleted_count} сообщений дайджеста")
                
            except Exception as e:
                logger.error(f"❌ Ошибка принудительного удаления: {e}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка принудительного удаления сообщений: {e}")
    
    async def _handle_approve_remaining(self, query, user_id: int):
        """Обработка одобрения оставшихся новостей."""
        try:
            logger.info(f"✅ Одобряем оставшиеся новости для пользователя {user_id}")
            
            if not hasattr(self, 'interactive_moderation_service') or not self.interactive_moderation_service:
                logger.error("❌ InteractiveModerationService недоступен")
                await query.answer("❌ Сервис модерации недоступен")
                return
            
            # УДАЛЯЕМ ВСЕ ЧАСТИ ДАЙДЖЕСТА ПЕРЕД ОДОБРЕНИЕМ
            chat_id = str(query.message.chat_id)
            logger.info(f"🗑️ Удаляем все части дайджеста для чата {chat_id} перед одобрением")
            
            if hasattr(self, 'morning_digest_service') and self.morning_digest_service:
                # Сначала пытаемся удалить через сессию
                cleanup_success = await self.morning_digest_service.delete_digest_messages(chat_id)
                
                # Если не удалось через сессию, принудительно удаляем по содержимому
                if not cleanup_success:
                    logger.warning(f"⚠️ Не удалось удалить через сессию, принудительно удаляем по содержимому")
                    await self._force_delete_digest_messages(chat_id)
                
                logger.info(f"✅ Все части дайджеста удалены для чата {chat_id}")
                
                # ТЕПЕРЬ очищаем сессию после удаления сообщений
                self.morning_digest_service.clear_digest_session(chat_id)
                logger.info(f"✅ Сессия дайджеста очищена для чата {chat_id}")
            else:
                logger.warning("⚠️ MorningDigestService недоступен для удаления дайджеста")
            
            # Завершаем модерацию и получаем одобренные новости
            approved_news = self.interactive_moderation_service.complete_moderation(user_id)
            logger.info(f"✅ Одобренные новости: {len(approved_news) if approved_news else 0}")
            
            if approved_news:
                # Показываем выбор эксперта
                await self._show_expert_choice(query, approved_news)
            else:
                await query.answer("❌ Нет одобренных новостей")
                
        except Exception as e:
            logger.error(f"❌ Ошибка при одобрении новостей: {e}")
            await query.answer("❌ Произошла ошибка")
    
    async def _handle_select_expert(self, query, user_id: int, expert_id: int):
        """Обработка выбора эксперта."""
        try:
            logger.info(f"👨‍💼 Обрабатываем выбор эксперта {expert_id} для пользователя {user_id}")
            
            if not hasattr(self, 'expert_choice_service') or not self.expert_choice_service:
                logger.error("❌ ExpertChoiceService недоступен")
                await query.answer("❌ Сервис выбора эксперта недоступен")
                return
            
            expert = self.expert_choice_service.get_expert_by_id(expert_id)
            logger.info(f"👨‍💼 Получен эксперт: {expert}")
            
            if not expert:
                logger.error("❌ Эксперт не найден")
                await query.answer("❌ Эксперт не найден")
                return
            
            logger.info(f"👨‍💼 Эксперт найден: {expert.name}, is_test: {expert.is_test}")
            
            if expert.is_test:
                # Сохраняем выбранного эксперта как эксперта недели
                logger.info(f"👨‍💼 Сохраняем эксперта {expert.name} как эксперта недели")
                self.service.set_expert_of_week(expert.id)
                
                # Тестовый эксперт - отправляем новости в личку
                logger.info(f"👨‍💼 Отправляем новости тестовому эксперту {expert.name}")
                await self._send_news_to_expert(query, expert, user_id)
            else:
                logger.info(f"⚠️ Эксперт {expert.name} пока недоступен")
                await query.answer("⚠️ Этот эксперт пока недоступен")
                
        except Exception as e:
            logger.error(f"❌ Ошибка при выборе эксперта: {e}")
            await query.answer("❌ Произошла ошибка")
    
    async def _update_moderation_message(self, query, remaining_news: List[Dict]):
        """Обновляет сообщение с оставшимися новостями."""
        try:
            logger.info(f"📝 Обновляем сообщение модерации, осталось новостей: {len(remaining_news)}")
            
            # Проверяем длину сообщения
            max_length = 4000
            
            # Создаем базовый заголовок
            header = f"""
🌅 <b>УТРЕННИЙ ДАЙДЖЕСТ НОВОСТЕЙ</b>
📰 Осталось новостей: {len(remaining_news)}

<b>📋 НОВОСТИ ДЛЯ МОДЕРАЦИИ:</b>
"""
            
            # Если новостей мало, отправляем как одно сообщение
            if len(remaining_news) <= 5:
                message_text = header
                
                # Добавляем оставшиеся новости
                for i, news in enumerate(remaining_news, 1):
                    message_text += f"""
<b>{i}. {news['title']}</b>
📝 {news['summary']}
➡️ Источник: {news['source_links']}

"""
                
                message_text += """
<b>💡 ИНСТРУКЦИИ:</b>
• Нажмите кнопку "🗑️ Удалить" для каждой ненужной новости
• После удаления ненужных новостей нажмите "✅ Одобрить оставшиеся"
"""
                
                # Создаем кнопки
                buttons = []
                for i, news in enumerate(remaining_news):
                    button_text = f"🗑️ Удалить {i+1}"
                    callback_data = f"remove_news_{news['id']}"
                    logger.info(f"🔘 Создаю кнопку: {button_text} -> {callback_data}")
                    buttons.append([
                        InlineKeyboardButton(
                            button_text, 
                            callback_data=callback_data
                        )
                    ])
                
                # Кнопка одобрения
                approve_button = InlineKeyboardButton(
                    "✅ Одобрить оставшиеся", 
                    callback_data="approve_remaining"
                )
                buttons.append([approve_button])
                
                reply_markup = InlineKeyboardMarkup(buttons)
                
                # Обновляем сообщение
                await query.edit_message_text(
                    text=message_text,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
                logger.info(f"✅ Сообщение модерации обновлено (одно сообщение)")
                
            else:
                # Новостей много, отправляем новое сообщение с разбиением
                await query.edit_message_text(
                    "📝 Обновляем дайджест...",
                    parse_mode="HTML"
                )
                
                # Создаем новый дайджест и отправляем его
                from src.services.morning_digest_service import MorningDigest, DigestNews
                from datetime import datetime
                
                # Создаем объекты DigestNews
                digest_news = []
                for news in remaining_news:
                    digest_item = DigestNews(
                        id=news['id'],
                        title=news['title'],
                        summary=news['summary'],
                        importance_score=news.get('importance_score', 5),
                        category=news.get('category', 'Общие'),
                        source_links=news.get('source_links', ''),
                        published_at=news.get('published_at', datetime.now()),
                        curator_id=news.get('curator_id')
                    )
                    digest_news.append(digest_item)
                
                # Создаем объект дайджеста
                digest = MorningDigest(
                    date=datetime.now(),
                    news_count=len(digest_news),
                    news_items=digest_news,
                    total_importance=5,
                    categories=['Общие'],
                    curator_id=None
                )
                
                # Отправляем новый дайджест через сервис
                success = await self.morning_digest_service.send_digest_to_curators_chat(
                    digest, 
                    str(query.message.chat_id)
                )
                
                if success:
                    logger.info(f"✅ Новый дайджест успешно отправлен после удаления новости")
                else:
                    logger.error(f"❌ Не удалось отправить новый дайджест после удаления новости")

            
        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении сообщения: {e}")
            await query.answer("❌ Ошибка обновления сообщения")
    
    async def _show_expert_choice(self, query, approved_news: List[Dict]):
        """Показывает выбор эксперта."""
        try:
            logger.info(f"👨‍💼 Показываем выбор эксперта для {len(approved_news)} новостей")
            
            if not hasattr(self, 'expert_choice_service') or not self.expert_choice_service:
                logger.error("❌ ExpertChoiceService недоступен")
                await query.edit_message_text("❌ Сервис выбора эксперта недоступен")
                return
            
            message_text = f"""
✅ <b>МОДЕРАЦИЯ ЗАВЕРШЕНА!</b>

📰 Одобрено новостей: {len(approved_news)}
👨‍💻 Выберите эксперта для комментариев:

"""
            
            # Создаем кнопки выбора эксперта
            buttons = self.expert_choice_service.create_expert_choice_buttons()
            logger.info(f"🔘 Создано кнопок выбора эксперта: {len(buttons)}")
            
            reply_markup = InlineKeyboardMarkup(buttons)
            
            # Отправляем новое сообщение вместо редактирования (старое уже удалено)
            await self.application.bot.send_message(
                chat_id=query.message.chat_id,
                text=message_text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            logger.info(f"✅ Сообщение выбора эксперта показано")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при показе выбора эксперта: {e}")
            await query.answer("❌ Ошибка показа выбора эксперта")
    
    async def _send_news_to_expert(self, query, expert, user_id: int):
        """Отправляет одобренные новости эксперту в личку."""
        try:
            logger.info(f"📤 Начинаем отправку новостей эксперту {expert.name} (ID: {expert.id})")
            
            # Проверяем доступность сервисов
            if not hasattr(self, 'interactive_moderation_service') or not self.interactive_moderation_service:
                logger.error("❌ InteractiveModerationService недоступен")
                await query.answer("❌ Сервис модерации недоступен")
                return
            
            if not hasattr(self, 'expert_interaction_service') or not self.expert_interaction_service:
                logger.error("❌ ExpertInteractionService недоступен")
                await query.answer("❌ Сервис взаимодействия с экспертами недоступен")
                return
            
            # Получаем одобренные новости из сессии
            approved_news = self.interactive_moderation_service.get_remaining_news(user_id)
            logger.info(f"📰 Получены одобренные новости: {len(approved_news)} штук")
            
            if not approved_news:
                logger.warning("⚠️ Нет одобренных новостей для отправки")
                await query.answer("❌ Нет одобренных новостей для отправки")
                return
            
            # Определяем ID эксперта для отправки
            if expert.is_test:
                # Для тестового эксперта используем его Telegram ID
                expert_telegram_id = int(expert.telegram_id)
                expert_name = expert.name
                logger.info(f"👨‍💼 Тестовый эксперт: {expert_name}, Telegram ID: {expert_telegram_id}")
            else:
                # Для реальных экспертов пока заглушка
                logger.info(f"⚠️ Реальный эксперт {expert.name} пока не подключен")
                await query.answer("⚠️ Реальные эксперты пока не подключены")
                return
            
            # Отправляем новости эксперту через новый сервис
            logger.info(f"📤 Отправляем {len(approved_news)} новостей эксперту {expert_name}")
            success = await self.expert_interaction_service.send_news_to_expert(
                expert_telegram_id, 
                approved_news, 
                expert_name
            )
            
            if success:
                logger.info(f"✅ Новости успешно отправлены эксперту {expert_name}")
                
                # Очищаем сессию модерации после успешной отправки
                if hasattr(self, 'interactive_moderation_service') and self.interactive_moderation_service:
                    self.interactive_moderation_service.cleanup_moderation_session(user_id)
                    logger.info(f"🧹 Сессия модерации для пользователя {user_id} очищена")
                
                # Обновляем сообщение в чате кураторов
                await query.edit_message_text(
                    text=f"✅ <b>Новости отправлены эксперту!</b>\n\n"
                         f"👨‍💻 <b>Эксперт:</b> {expert.name}\n"
                         f"📰 <b>Количество новостей:</b> {len(approved_news)}\n"
                         f"📤 <b>Статус:</b> Отправлено в личку\n\n"
                         f"⏰ <b>Ожидаем комментарии эксперта...</b>",
                    parse_mode="HTML"
                )
                
                await query.answer(f"✅ Новости отправлены эксперту {expert.name}")
            else:
                logger.error(f"❌ Ошибка отправки новостей эксперту {expert_name}")
                await query.answer("❌ Ошибка отправки новостей эксперту")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке новостей эксперту: {e}")
            await query.answer("❌ Произошла ошибка")
    
    async def _handle_comment_request(self, query, expert_id: int, news_id: int):
        """Обрабатывает запрос эксперта на комментирование новости."""
        try:
            if not hasattr(self, 'expert_interaction_service') or not self.expert_interaction_service:
                await query.answer("❌ Сервис взаимодействия с экспертами недоступен")
                return
            
            # Получаем инструкции для комментирования
            instructions = await self.expert_interaction_service.handle_comment_request(expert_id, news_id)
            
            # Отправляем инструкции эксперту
            await query.message.reply_text(
                text=instructions,
                parse_mode="HTML"
            )
            
            await query.answer("💬 Готовы к комментированию!")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при обработке запроса на комментирование: {e}")
            await query.answer("❌ Произошла ошибка")
    
    # ==================== ЗАПУСК БОТА ====================
    
    
    async def schedule_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /schedule_status - статус планировщика."""
        user = update.effective_user
        
        logger.info(f"📊 Команда /schedule_status от пользователя {user.id}")
        
        try:
            # Проверяем права куратора
            if not await self._is_curator(user.id):
                await update.message.reply_text("❌ У вас нет прав для просмотра статуса планировщика!")
                return
            
            # Получаем сервис планировщика
            scheduler_service = self._get_scheduler_service()
            if not scheduler_service:
                await update.message.reply_text("❌ Сервис планировщика недоступен!")
                return
            
            # Получаем статус
            status = scheduler_service.get_status()
            
            response = f"📊 Статус планировщика\n\n"
            response += f"🔄 Статус: {'✅ Запущен' if status.get('is_running') else '❌ Остановлен'}\n"
            response += f"📅 Следующий дайджест: {status.get('next_morning_digest', 'Не установлено')}\n"
            response += f"📋 Задач в очереди: {status.get('jobs_count', 0)}\n"
            response += f"💬 Чат кураторов: ID {scheduler_service.morning_digest_service.curators_chat_id}\n\n"
            response += f"📋 Доступные команды:\n"
            response += f"`schedule` - Запустить планировщик\n"
            response += f"`morning_digest` - Отправить дайджест сейчас"
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"❌ Ошибка в schedule_status_command: {e}")
            await update.message.reply_text(f"❌ Ошибка получения статуса: {e}")
    
    async def _is_curator(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь куратором."""
        try:
            # Для тестирования считаем всех пользователей кураторами
            # В реальной системе здесь должна быть проверка в базе данных
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка проверки прав куратора: {e}")
            return False
 
    async def proxy_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает статус ProxyAPI сервиса."""
        try:
            # Получаем статус ProxyAPI через AIAnalysisService
            if hasattr(self, 'ai_analysis_service'):
                status = self.ai_analysis_service.get_proxy_status()
            else:
                status = {
                    "service": "AIAnalysisService",
                    "proxy_available": False,
                    "message": "Сервис AI анализа недоступен"
                }
            
            # Форматируем ответ
            status_text = f"""
🔍 <b>Статус ProxyAPI сервиса</b>

📊 <b>Сервис:</b> {status.get('service', 'Неизвестно')}
🚀 <b>ProxyAPI доступен:</b> {'✅ Да' if status.get('proxy_available') else '❌ Нет'}

"""
            
            if status.get('proxy_available'):
                status_text += f"""
🔗 <b>Прокси URL:</b> <code>{status.get('proxy_url', 'Не указан')}</code>
🔑 <b>ProxyAPI ключ установлен:</b> {'✅ Да' if status.get('proxy_api_key_set') else '❌ Нет'}
🤖 <b>Клиент инициализирован:</b> {'✅ Да' if status.get('client_initialized') else '❌ Нет'}

✅ <b>ProxyAPI работает и будет использован для AI анализа!</b>
"""
            else:
                status_text += f"""
⚠️ <b>ProxyAPI недоступен</b>

📝 <b>Для настройки ProxyAPI:</b>
1. Получите прокси URL от вашего провайдера
2. Добавьте в .env файл:
   PROXY_API_URL=https://your-proxy-domain.com/v1
   PROXY_API_KEY=sk-your-proxy-key
3. Перезапустите бота

ℹ️ <b>Текущий режим:</b> Fallback анализ (без AI)
"""
            
            await update.message.reply_text(status_text, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в proxy_status_command: {e}")
            await update.message.reply_text(
                "❌ Ошибка при получении статуса ProxyAPI. Проверьте логи."
            )
    
    # ==================== ЗАПУСК БОТА ====================
    
    async def run(self):
        """Запуск бота."""
        logger.info("🚀 Запуск AI News Assistant Bot...")
        
        try:
            # Инициализируем и запускаем бота
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            logger.info("✅ Бот успешно запущен!")
            
            # Автоматически запускаем планировщик при старте бота
            logger.info(f"🔍 Проверяем SchedulerService: {self.scheduler_service}")
            
            if self.scheduler_service:
                try:
                    logger.info("🚀 Запускаем планировщик...")
                    await self.scheduler_service.start()
                    logger.info("✅ Планировщик автоматически запущен при старте бота")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось автоматически запустить планировщик: {e}")
                    logger.warning(f"⚠️ Тип ошибки: {type(e).__name__}")
                    import traceback
                    logger.warning(f"⚠️ Полный traceback: {traceback.format_exc()}")
                    logger.info("ℹ️ Планировщик можно запустить вручную командой /schedule")
            else:
                logger.warning("⚠️ SchedulerService недоступен - планировщик не будет работать")
                logger.warning("🔍 Проверьте логи выше для диагностики проблемы")
            
            # Держим бота запущенным
            import asyncio
            while True:
                await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"❌ Ошибка при запуске бота: {e}")
            raise
    
    async def stop(self):
        """Остановка бота."""
        logger.info("🛑 Остановка бота...")
        
        try:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            
            logger.info("✅ Бот успешно остановлен!")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при остановке бота: {e}")
            raise
    
    async def _update_message_fallback(self, query, remaining_news: List[Dict]):
        """
        Fallback метод для обновления сообщения с сокращенным текстом.
        
        Args:
            query: Callback query
            remaining_news: Список оставшихся новостей
        """
        try:
            # Создаем сокращенный текст
            short_text = f"""
🌅 <b>УТРЕННИЙ ДАЙДЖЕСТ НОВОСТЕЙ</b>
📰 Осталось новостей: {len(remaining_news)}

<b>📋 НОВОСТИ ДЛЯ МОДЕРАЦИИ:</b>
"""
            # Добавляем только первые 3 новости для экономии места
            for i, news in enumerate(remaining_news[:3], 1):
                short_text += f"""
<b>{i}. {news['title'][:50]}...</b>
"""
            
            if len(remaining_news) > 3:
                short_text += f"\n... и еще {len(remaining_news) - 3} новостей"
            
            short_text += """
<b>💡 ИНСТРУКЦИИ:</b>
• Нажмите кнопку "🗑️ Удалить" для каждой ненужной новости
• После удаления ненужных новостей нажмите "✅ Одобрить оставшиеся"
"""
            
            # Создаем кнопки только для первых 3 новостей
            buttons = []
            for i, news in enumerate(remaining_news[:3]):
                button_text = f"🗑️ Удалить {i+1}"
                callback_data = f"remove_news_{news['id']}"
                buttons.append([
                    InlineKeyboardButton(
                        button_text, 
                        callback_data=callback_data
                    )
                ])
            
            # Кнопка одобрения
            approve_button = InlineKeyboardButton(
                "✅ Одобрить оставшиеся", 
                callback_data="approve_remaining"
            )
            buttons.append([approve_button])
            
            reply_markup = InlineKeyboardMarkup(buttons)
            
            # Обновляем сообщение
            await query.edit_message_text(
                text=short_text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            logger.info(f"✅ Сообщение обновлено с fallback (сокращенный текст)")
            
        except Exception as fallback_error:
            logger.error(f"❌ Ошибка fallback обновления: {fallback_error}")
            await query.answer("❌ Ошибка обновления дайджеста")
    
    async def _create_new_digest_after_removal(self, query, remaining_news: List[Dict]):
        """
        Создает новый дайджест после удаления новости.
        
        Args:
            query: CallbackQuery от Telegram
            remaining_news: Список оставшихся новостей
        """
        try:
            logger.info(f"🔄 Создаем новый дайджест после удаления новости, осталось: {len(remaining_news)}")
            
            # Создаем объекты DigestNews
            from src.services.morning_digest_service import MorningDigest, DigestNews
            from datetime import datetime
            
            digest_news = []
            for news in remaining_news:
                digest_item = DigestNews(
                    id=news['id'],
                    title=news['title'],
                    summary=news['summary'],
                    importance_score=news.get('importance_score', 5),
                    category=news.get('category', 'Общие'),
                    source_links=news['source_links'],
                    published_at=news.get('published_at', datetime.now()),
                    curator_id=news.get('curator_id')
                )
                digest_news.append(digest_item)
            
            # Создаем объект дайджеста
            digest = MorningDigest(
                date=datetime.now(),
                news_count=len(digest_news),
                news_items=digest_news,
                total_importance=5,
                categories=['Общие']
            )
            
            # Отправляем новый дайджест через сервис
            success = await self.morning_digest_service.send_digest_to_curators_chat(
                digest, 
                str(query.message.chat_id)
            )
            
            if success:
                logger.info(f"✅ Новый дайджест успешно отправлен после удаления новости")
            else:
                logger.error(f"❌ Не удалось отправить новый дайджест после удаления новости")
                
        except Exception as e:
            logger.error(f"❌ Ошибка создания нового дайджеста после удаления: {e}")
    
    # ==================== МЕТОДЫ ДЛЯ ПАРСИНГА ====================
    
    async def parse_now_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /parse_now - запуск парсинга всех каналов за 24 часа."""
        user = update.effective_user
        
        logger.info(f"📰 Команда /parse_now от пользователя {user.id}")
        
        try:
            # Проверяем права куратора
            if not await self._is_curator(user.id):
                await update.message.reply_text("❌ У вас нет прав для запуска парсинга!")
                return
            
            # Получаем сервис парсинга
            if not hasattr(self, 'parser_service') or not self.parser_service:
                await update.message.reply_text("❌ Сервис парсинга недоступен!")
                return
            
            # Отправляем сообщение о начале парсинга
            await update.message.reply_text("🔄 Запускаем парсинг всех каналов за последние 24 часа...")
            
            # Запускаем парсинг
            stats = await self.parser_service.parse_all_sources()
            
            if stats:
                # Формируем отчет
                total_news = sum(stats.values())
                report = f"✅ Парсинг завершен!\n\n"
                report += f"📊 Всего новостей: {total_news}\n\n"
                report += f"📈 По источникам:\n"
                
                for source_name, count in stats.items():
                    report += f"• {source_name}: {count} новостей\n"
                
                await update.message.reply_text(report)
            else:
                await update.message.reply_text("⚠️ Парсинг завершен, но новых новостей не найдено.")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в parse_now_command: {e}")
            await update.message.reply_text(f"❌ Ошибка при парсинге: {e}")
    
    # ==================== МЕТОДЫ ДЛЯ ФИНАЛЬНОГО ДАЙДЖЕСТА ====================
    
    async def create_final_digest_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для создания финального дайджеста."""
        try:
            logger.info("🎨 Команда создания финального дайджеста")
            
            if not self.final_digest_formatter or not self.curator_approval_service:
                await update.message.reply_text("❌ Сервис финального форматирования недоступен")
                return
            
            await update.message.reply_text("🔄 Создание финального дайджеста...")
            
            # Получаем реальные данные из базы данных
            logger.info("📊 Получаем реальные данные из базы данных...")
            
            # 1. Получаем одобренные новости
            approved_news = self.service.get_approved_news_for_digest()
            if not approved_news:
                await update.message.reply_text("❌ Нет одобренных новостей для создания дайджеста")
                return
            
            # 2. Получаем эксперта недели
            expert_of_week = self.service.get_expert_of_week()
            if not expert_of_week:
                await update.message.reply_text("❌ Не выбран эксперт недели")
                return
            
            # 3. Получаем комментарии экспертов к новостям
            expert_comments = self.service.get_expert_comments_for_news([news.id for news in approved_news])
            
            # 4. Получаем источники новостей
            news_sources = self.service.get_news_sources([news.id for news in approved_news])
            
            logger.info(f"📊 Получено {len(approved_news)} новостей, эксперт: {expert_of_week.name}, комментариев: {len(expert_comments)}")
            
            # Создаем финальный дайджест
            formatted_digest = self.final_digest_formatter.create_final_digest(
                approved_news=approved_news,
                expert_comments=expert_comments,
                expert_of_week=expert_of_week,
                news_sources=news_sources
            )
            
            logger.info("✅ Финальный дайджест создан, отправляем на согласование...")
            
            # Отправляем дайджест на согласование куратору
            result = await self.curator_approval_service.send_digest_for_approval(
                formatted_digest=formatted_digest,
                chat_id=str(self.curator_chat_id)
            )
            
            if result.get("success"):
                await update.message.reply_text("✅ Финальный дайджест создан и отправлен на согласование куратору!")
                logger.info("🎯 Дайджест успешно отправлен на согласование")
            else:
                await update.message.reply_text("❌ Ошибка при отправке дайджеста на согласование")
                logger.error(f"❌ Ошибка отправки: {result.get('error', 'Неизвестная ошибка')}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка команды создания финального дайджеста: {e}")
            await update.message.reply_text("❌ Произошла ошибка при создании дайджеста")
    
    async def _handle_digest_approval(self, query, user_id: int):
        """Обработка одобрения финального дайджеста куратором."""
        try:
            logger.info(f"✅ Куратор {user_id} одобрил финальный дайджест")
            
            if not self.curator_approval_service:
                await query.answer("❌ Сервис согласования недоступен")
                return
            
            # Обрабатываем одобрение через сервис
            result = await self.curator_approval_service.handle_approval("approve_digest", str(user_id))
            
            if result["success"]:
                await query.answer("✅ Дайджест одобрен! Ожидаем фото для публикации.")
            else:
                await query.answer(f"❌ Ошибка: {result['error']}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки одобрения дайджеста: {e}")
            await query.answer("❌ Произошла ошибка")
    
    async def _handle_digest_editing(self, query, user_id: int):
        """Обработка запроса на редактирование дайджеста."""
        try:
            logger.info(f"✏️ Куратор {user_id} запросил редактирование дайджеста")
            
            if not self.curator_approval_service:
                await query.answer("❌ Сервис согласования недоступен")
                return
            
            # Устанавливаем состояние ожидания правок
            self.waiting_for_digest_edit[user_id] = True
            logger.info(f"🔄 Установлено состояние ожидания правок для пользователя {user_id}")
            
            # Обрабатываем запрос на редактирование через сервис
            result = await self.curator_approval_service.handle_approval("edit_digest", str(user_id))
            
            if result["success"]:
                await query.answer("✏️ Ожидаем исправленный текст дайджеста")
            else:
                await query.answer(f"❌ Ошибка: {result['error']}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки запроса на редактирование: {e}")
            await query.answer("❌ Произошла ошибка")
    
    async def _handle_digest_edit_message(self, update: Update, user_id: int, text: str):
        """Обработка сообщения с правками дайджеста."""
        try:
            logger.info(f"📝 Обработка правок дайджеста от пользователя {user_id}")
            
            if not self.curator_approval_service:
                await update.message.reply_text("❌ Сервис согласования недоступен")
                return
            
            # Обрабатываем правки через сервис
            result = await self.curator_approval_service.process_edited_digest(text, str(user_id))
            
            if result["success"]:
                # Убираем состояние ожидания правок
                if user_id in self.waiting_for_digest_edit:
                    del self.waiting_for_digest_edit[user_id]
                    logger.info(f"🔄 Снято состояние ожидания правок для пользователя {user_id}")
                
                await update.message.reply_text("✅ Правки обработаны! Исправленный дайджест отправлен на согласование.")
            else:
                await update.message.reply_text(f"❌ Ошибка обработки правок: {result['error']}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки правок дайджеста: {e}")
            await update.message.reply_text("❌ Произошла ошибка при обработке правок")
    
    async def _handle_photo_for_publication(self, update: Update, user_id: int):
        """Обработка фото для публикации дайджеста."""
        try:
            logger.info(f"📸 Обработка фото для публикации от пользователя {user_id}")
            
            # Получаем digest_text из состояния ожидания
            digest_text = self.waiting_for_photo.get(user_id)
            if not digest_text:
                await update.message.reply_text("❌ Ошибка: не найден текст дайджеста для публикации")
                return
            
            # Получаем file_id самого большого фото
            photo = update.message.photo[-1]  # Берем фото с наивысшим разрешением
            photo_file_id = photo.file_id
            
            logger.info(f"📸 Получено фото с file_id: {photo_file_id}")
            
            # Публикуем дайджест с фото через PublicationService
            logger.info(f"🔍 Проверка PublicationService: hasattr={hasattr(self, 'publication_service')}, service={self.publication_service}")
            if hasattr(self, 'publication_service') and self.publication_service:
                logger.info(f"📤 Вызываем publish_digest_with_photo с digest_text длиной {len(digest_text)} и photo_file_id {photo_file_id}")
                result = await self.publication_service.publish_digest_with_photo(digest_text, photo_file_id)
                logger.info(f"📤 Результат публикации: {result}")
                
                if result["success"]:
                    # Убираем состояние ожидания фото
                    if user_id in self.waiting_for_photo:
                        del self.waiting_for_photo[user_id]
                        logger.info(f"🔄 Снято состояние ожидания фото для пользователя {user_id}")
                    
                    await update.message.reply_text("🎉 Дайджест успешно опубликован в канал с фото!")
                    logger.info(f"✅ Дайджест опубликован в канал с message_id: {result['message_id']}")
                else:
                    await update.message.reply_text(f"❌ Ошибка публикации: {result['error']}")
            else:
                logger.error("❌ PublicationService недоступен")
                await update.message.reply_text("❌ Сервис публикации недоступен")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки фото для публикации: {e}")
            await update.message.reply_text("❌ Произошла ошибка при публикации дайджеста")
    
    async def _handle_edited_digest_approval(self, query, user_id: int):
        """Обработка одобрения исправленного дайджеста."""
        try:
            logger.info(f"✅ Куратор {user_id} одобрил исправленный дайджест")
            
            if not self.curator_approval_service:
                await query.answer("❌ Сервис согласования недоступен")
                return
            
            # Обрабатываем одобрение исправленного дайджеста
            result = await self.curator_approval_service.handle_approval("approve_edited_digest", str(user_id))
            
            if result["success"]:
                await query.answer("✅ Исправленный дайджест одобрен! Ожидаем фото для публикации.")
            else:
                await query.answer(f"❌ Ошибка: {result['error']}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки одобрения исправленного дайджеста: {e}")
            await query.answer("❌ Произошла ошибка")


# ==================== ФУНКЦИЯ ЗАПУСКА ====================

async def main():
    """Основная функция запуска."""
    # Получаем токен из переменных окружения
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # Временное решение: используем токен напрямую
    if not token:
        token = "8195833718:AAGbqnbZz7NrbOWN5ic5k7oxGMUTntgHE6s"
        logger.info("🔧 Используем токен из кода (временное решение)")
    
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
        logger.error("Создайте файл .env и добавьте TELEGRAM_BOT_TOKEN=your_token_here")
        return
    
    # Создаем и запускаем бота
    bot = AINewsBot(token)
    
    # Делаем бот доступным глобально для других модулей
    import sys
    current_module = sys.modules[__name__]
    current_module.bot_instance = bot
    logger.info("✅ Бот сделан доступным глобально")
    
    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("🛑 Получен сигнал остановки...")
        await bot.stop()
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        await bot.stop()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 