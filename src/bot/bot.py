#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram бот для AI News Assistant.
"""

import os
import logging
import asyncio
from datetime import datetime

# Добавляем путь к модулям
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

from src.services.postgresql_database_service import PostgreSQLDatabaseService
from src.services.news_parser_service import NewsParserService
from src.services.interactive_moderation_service import InteractiveModerationService
from src.services.expert_choice_service import ExpertChoiceService
from src.services.expert_interaction_service import ExpertInteractionService
from src.services.morning_digest_service import MorningDigestService
from src.services.final_digest_formatter_service import FinalDigestFormatterService
from src.services.curator_approval_service import CuratorApprovalService
from src.config import config
from src.services.ai_analysis_service import AIAnalysisService
from src.services.scheduler_service import SchedulerService


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
    """
    
    def __init__(self, token: str):
        """
        Инициализация бота.
        
        Args:
            token (str): Токен Telegram бота
        """
        self.token = token
        self.application = Application.builder().token(token).build()
        self.service = PostgreSQLDatabaseService()
        
        # Состояние ожидания правок дайджеста
        self.waiting_for_digest_edit = {}  # user_id -> True
        
        # Состояние ожидания фото для публикации
        self.waiting_for_photo = {}  # user_id -> digest_text
        
        # OpenAI сервис больше не нужен, используем AIAnalysisService
        logger.info("ℹ️ OpenAI сервис отключен, используем AIAnalysisService с ProxyAPI")
        
        
        # Инициализируем NewsParserService для автоматического парсинга новостей
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
            ai_analysis_service=self.ai_analysis_service
        )
        logger.info("✅ NewsParserService подключен для автоматического парсинга с PostgreSQL")

        # Инициализируем SchedulerService для автоматических задач
        try:
            logger.info("🔧 Начинаем инициализацию SchedulerService...")
            
            logger.info("✅ Модули SchedulerService импортированы")
            
            # Проверяем доступность parser_service
            if self.parser_service:
                logger.info("✅ NewsParserService доступен для SchedulerService")
            else:
                logger.warning("⚠️ NewsParserService недоступен для SchedulerService")
            
            self.morning_digest_service = MorningDigestService(
                database_service=postgres_db,
                ai_analysis_service=self.ai_analysis_service,
                bot=self.application.bot
            )
            logger.info("✅ MorningDigestService создан")
            
            # Инициализируем новые сервисы для финального форматирования
            if self.ai_analysis_service:
                self.final_digest_formatter = FinalDigestFormatterService(self.ai_analysis_service)
                logger.info("✅ FinalDigestFormatterService создан")
                
                # Получаем токен бота и ID кураторского чата
                bot_token = config.telegram.bot_token
                curator_chat_id = config.telegram.curator_chat_id
                self.curator_chat_id = curator_chat_id  # Сохраняем как атрибут класса
                
                self.curator_approval_service = CuratorApprovalService(
                    bot_token=bot_token,
                    curator_chat_id=curator_chat_id,
                    formatter_service=self.final_digest_formatter,
                    bot_instance=self  # Передаем ссылку на бот
                )
                logger.info("✅ CuratorApprovalService создан")
                
                # Создаем expert_interaction_service с curator_approval_service
                self.expert_interaction_service = ExpertInteractionService(
                    self.application.bot, 
                    self.curator_approval_service
                )
                logger.info("✅ ExpertInteractionService создан с CuratorApprovalService")
            else:
                logger.warning("⚠️ AIAnalysisService недоступен, финальное форматирование отключено")
                self.final_digest_formatter = None
                self.curator_approval_service = None
                self.expert_interaction_service = None
            
            
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
            logger.info("✅ Сервисы интерактивной модерации подключены")
        except Exception as e:
            logger.error(f"❌ Ошибка создания сервисов модерации: {e}")
            self.interactive_moderation_service = None
            self.expert_choice_service = None
        
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
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на inline кнопки."""
        query = update.callback_query
        
        # Безопасно отвечаем на callback query с обработкой ошибок
        try:
            await query.answer()
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при ответе на callback query: {e}")
            # Продолжаем выполнение даже если не удалось ответить
        
        data = query.data
        logger.info(f"🔘 Обработка callback: {data}")
        
        if data.startswith("remove_news_"):
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
            # Получаем необходимые сервисы
            postgres_db = self._get_postgres_db()
            
            # Создаем сервис дайджеста
            digest_service = MorningDigestService(
                database_service=postgres_db,
                ai_analysis_service=self.ai_analysis_service,
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
            curators_chat_id = config.telegram.curator_chat_id
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
    
    async def _create_new_digest_after_removal(self, query, remaining_news):
        """Создает новый дайджест с оставшимися новостями после удаления."""
        try:
            logger.info(f"🔄 Создаем новый дайджест с {len(remaining_news)} оставшимися новостями")
            
            # Создаем объекты DigestNews из оставшихся новостей
            digest_news = []
            for i, news in enumerate(remaining_news):
                from src.services.morning_digest_service import DigestNews
                digest_item = DigestNews(
                    id=news.get('id', 0),
                    title=news.get('title', 'Заголовок не найден'),
                    summary=news.get('summary', 'Саммари не найдено'),
                    source_links=news.get('source_links', ''),
                    published_at=datetime.now(),
                    curator_id=None
                )
                digest_news.append(digest_item)
            
            # Создаем новый дайджест
            from src.services.morning_digest_service import MorningDigest
            new_digest = MorningDigest(
                date=datetime.now(),
                news_count=len(digest_news),
                news_items=digest_news,
                curator_id=None
            )
            
            # Создаем сообщение с новым дайджестом
            message_text, buttons = self.morning_digest_service.create_interactive_digest_message(new_digest)
            
            # Очищаем текст от HTML тегов
            cleaned_text = self.morning_digest_service._clean_html_text(message_text)
            
            # Отправляем новое сообщение вместо редактирования
            from telegram import InlineKeyboardMarkup
            reply_markup = InlineKeyboardMarkup(buttons)
            
            # Отправляем новое сообщение в тот же чат
            await query.message.chat.send_message(
                text=cleaned_text,
                reply_markup=reply_markup
            )
            
            logger.info(f"✅ Новый дайджест создан и отправлен с {len(digest_news)} новостями")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания нового дайджеста: {e}")
            await query.answer("❌ Ошибка создания нового дайджеста")
    
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
            return PostgreSQLDatabaseService()
        except Exception as e:
            logger.error(f"❌ Ошибка получения PostgreSQL сервиса: {e}")
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
                    try:
                        logger.info(f"🗑️ Принудительно удаляем сообщения дайджеста для чата: {chat_id}")
                        
                        if not hasattr(self, 'morning_digest_service') or not self.morning_digest_service:
                            logger.warning("⚠️ MorningDigestService недоступен")
                            return
                        
                        # Принудительное удаление отключено (метод get_chat_history недоступен)
                        logger.info("ℹ️ Принудительное удаление отключено")
                            
                    except Exception as e:
                        logger.error(f"❌ Ошибка принудительного удаления сообщений: {e}")
                
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
                await self._show_expert_choice(query, user_id, approved_news)
            else:
                await query.answer("❌ Нет одобренных новостей")
                
        except Exception as e:
            logger.error(f"❌ Ошибка при одобрении новостей: {e}")
            await query.answer("❌ Произошла ошибка")
    
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
            
            # Публикуем дайджест с фото напрямую
            try:
                # Получаем токен бота и ID канала
                bot_token = config.telegram.bot_token
                channel_id = config.telegram.channel_id
                
                # Обрезаем текст для подписи (лимит Telegram: 1024 символа)
                max_caption_length = config.telegram.max_photo_caption_length
                if len(digest_text) > max_caption_length:
                    caption_text = digest_text[:max_caption_length - 3] + "..."
                    logger.info(f"📝 Текст подписи обрезан с {len(digest_text)} до {len(caption_text)} символов")
                else:
                    caption_text = digest_text
                
                # Отправляем фото с подписью
                await self.application.bot.send_photo(
                    chat_id=channel_id,
                    photo=photo_file_id,
                    caption=caption_text,
                    parse_mode="HTML"
                )
                
                # Убираем состояние ожидания фото
                if user_id in self.waiting_for_photo:
                    del self.waiting_for_photo[user_id]
                    logger.info(f"🔄 Снято состояние ожидания фото для пользователя {user_id}")
                
                await update.message.reply_text("🎉 Дайджест успешно опубликован в канал с фото!")
                logger.info(f"✅ Дайджест опубликован в канал")
                
            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка публикации: {str(e)}")
                logger.error(f"❌ Ошибка публикации дайджеста: {e}")
                
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

    async def _show_expert_choice(self, query, user_id: int, approved_news: list):
        """
        Показывает выбор эксперта для одобренных новостей.
        
        Args:
            query: Callback query
            user_id: ID пользователя
            approved_news: Список одобренных новостей
        """
        try:
            logger.info(f"👨‍💻 Показываем выбор эксперта для {len(approved_news)} новостей")
            
            # Получаем кнопки для выбора эксперта
            buttons = self.expert_choice_service.create_expert_choice_buttons()
            
            # Создаем сообщение
            message_text = f"""
✅ НОВОСТИ ОДОБРЕНЫ!

📰 Количество новостей: {len(approved_news)}

👨‍💻 Выберите эксперта для комментирования:
"""
            
            # Отправляем сообщение с кнопками выбора эксперта
            from telegram import InlineKeyboardMarkup
            reply_markup = InlineKeyboardMarkup(buttons)
            
            await query.message.reply_text(
                text=message_text,
                reply_markup=reply_markup
            )
            
            logger.info(f"✅ Выбор эксперта показан для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа выбора эксперта: {e}")
            await query.answer("❌ Ошибка при выборе эксперта")


# ==================== ФУНКЦИЯ ЗАПУСКА ====================

async def main():
    """Основная функция запуска."""
    # Получаем токен из переменных окружения
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
        logger.error("Создайте файл .env и добавьте TELEGRAM_BOT_TOKEN=your_token_here")
        return
    
    # Создаем и запускаем бота
    bot = AINewsBot(token)
    
    
    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("🛑 Получен сигнал остановки...")
        await bot.stop()
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main()) 