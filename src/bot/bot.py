#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram бот для AI News Assistant.
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import List

# Добавляем путь к модулям
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

from src.services.database_singleton import get_database_service
from src.services.news_parser_service import NewsParserService
from src.services.interactive_moderation_service import InteractiveModerationService
from src.services.expert_choice_service import ExpertChoiceService
from src.services.expert_interaction_service import ExpertInteractionService
from src.services.morning_digest_service import MorningDigestService
from src.services.final_digest_formatter_service import FinalDigestFormatterService
from src.services.curator_approval_service import CuratorApprovalService
from src.config import config
from src.services.bot_session_service import bot_session_service
from src.services.ai_analysis_service import AIAnalysisService
from src.services.scheduler_service import SchedulerService
from src.utils.bot_utils import BotUtils


# ==================== НАСТРОЙКА ЛОГИРОВАНИЯ ====================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Отключаем избыточное логирование внешних библиотек
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.dialects').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram.ext').setLevel(logging.WARNING)
logging.getLogger('apscheduler').setLevel(logging.WARNING)
logging.getLogger('telethon').setLevel(logging.WARNING)
logging.getLogger('telethon.network').setLevel(logging.ERROR)
logging.getLogger('telethon.client').setLevel(logging.WARNING)

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
        self.service = get_database_service()
        
        # ✅ Используем BotSessionService для управления состояниями
        self.session_service = bot_session_service
        
        # Инициализируем все сервисы
        self._init_services()
        
        # Настройка обработчиков
        self._setup_handlers()
    
    def _init_services(self):
        """Инициализация всех сервисов бота."""
        logger.info("🔧 Начинаем инициализацию сервисов...")
        
        # Инициализируем AI сервис
        self._init_ai_services()
        
        # Инициализируем основные сервисы
        self._init_core_services()
        
        # Инициализируем сервисы планировщика
        self._init_scheduler_services()
        
        # Инициализируем сервисы модерации
        self._init_moderation_services()
        
        logger.info("✅ Все сервисы инициализированы")
    
    def _init_ai_services(self):
        """Инициализация AI сервисов."""
        try:
            self.ai_analysis_service = AIAnalysisService()
            logger.info("✅ AIAnalysisService подключен для анализа новостей")
        except Exception as e:
            logger.error(f"❌ Ошибка создания AIAnalysisService: {e}")
            self.ai_analysis_service = None
    
    def _init_core_services(self):
        """Инициализация основных сервисов."""
        # NewsParserService
        self.parser_service = NewsParserService(
            database_service=self.service,
            ai_analysis_service=self.ai_analysis_service
        )
        logger.info("✅ NewsParserService подключен для автоматического парсинга с PostgreSQL")
        
        # MorningDigestService
        self.morning_digest_service = MorningDigestService(
            database_service=self.service,
            ai_analysis_service=self.ai_analysis_service,
            bot=self.application.bot
        )
        logger.info("✅ MorningDigestService создан")
    
    def _init_scheduler_services(self):
        """Инициализация сервисов планировщика."""
        try:
            logger.info("🔧 Начинаем инициализацию SchedulerService...")
            
            # Инициализируем сервисы для финального форматирования
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
            
            # SchedulerService
            self.scheduler_service = SchedulerService(
                morning_digest_service=self.morning_digest_service,
                news_parser_service=self.parser_service
            )
            logger.info("✅ SchedulerService подключен для автоматических задач")
            logger.info("📱 Автоматический парсинг новостей включен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания SchedulerService: {e}")
            logger.error(f"❌ Тип ошибки: {type(e).__name__}")
            import traceback
            logger.error(f"❌ Полный traceback: {traceback.format_exc()}")
            self.scheduler_service = None
    
    def _init_moderation_services(self):
        """Инициализация сервисов модерации."""
        try:
            self.interactive_moderation_service = InteractiveModerationService()
            self.expert_choice_service = ExpertChoiceService()
            logger.info("✅ Сервисы интерактивной модерации подключены")
        except Exception as e:
            logger.error(f"❌ Ошибка создания сервисов модерации: {e}")
            self.interactive_moderation_service = None
            self.expert_choice_service = None
    
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
        await BotUtils.safe_answer_callback(query)
        
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
        elif data == "show_full_digest":
            # Обработка показа полного дайджеста
            logger.info(f"📖 Показываем полный дайджест")
            await self._handle_show_full_digest(query, query.from_user.id)
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
            # Используем уже созданный единственный экземпляр БД сервиса
            digest_service = MorningDigestService(
                database_service=self.service,
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
                await self.interactive_moderation_service.create_moderation_session(
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
    
    
    async def _handle_remove_news(self, query, user_id: int, news_id: int):
        """Обработка удаления новости."""
        try:
            logger.info(f"🗑️ Удаляем новость {news_id} для пользователя {user_id}")
            
            # Проверяем доступность сервиса модерации
            if not await BotUtils.check_service_availability_simple(
                self.interactive_moderation_service, 
                "InteractiveModerationService", 
                query
            ):
                return
            
            # Удаляем новость из сессии модерации
            success = await self.interactive_moderation_service.remove_news_from_session(user_id, news_id)
            if not success:
                await query.answer("❌ Не удалось удалить новость")
                return
            
            # Получаем оставшиеся новости
            remaining_news = await self.interactive_moderation_service.get_remaining_news(user_id)
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
            for i, news in enumerate(remaining_news, 1):  # Начинаем с 1 для правильной нумерации
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
            
            # Сначала удаляем ВСЕ сообщения дайджеста
            try:
                chat_id_str = str(query.message.chat_id)
                cleanup_success = await self.morning_digest_service.delete_digest_messages(chat_id_str)
                if cleanup_success:
                    logger.info("🗑️ Все сообщения дайджеста удалены")
                else:
                    logger.warning("⚠️ Не удалось удалить все сообщения дайджеста, удаляем только текущее")
                    await query.message.delete()
            except Exception as e:
                logger.warning(f"⚠️ Ошибка удаления сообщений дайджеста: {e}")
                try:
                    await query.message.delete()
                except:
                    pass
            
            # Создаем сообщение с новым дайджестом
            message_text, buttons = self.morning_digest_service.create_interactive_digest_message(new_digest)
            
            # Очищаем текст от HTML тегов
            cleaned_text = self.morning_digest_service._clean_html_text(message_text)
            
            # Проверяем длину сообщения и разбиваем на части если нужно
            max_length = config.telegram.max_message_length
            
            if len(cleaned_text) <= max_length:
                # Сообщение помещается в один пост
                from telegram import InlineKeyboardMarkup
                reply_markup = InlineKeyboardMarkup(buttons)
                
                message = await query.message.chat.send_message(
                    text=cleaned_text,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
                
                # ВАЖНО: Сохраняем ID нового сообщения в сессию
                self.morning_digest_service._save_digest_session(
                    str(query.message.chat.id), 
                    [message.message_id], 
                    new_digest.news_count
                )
                logger.info(f"💾 Обновлена сессия с новым ID сообщения: {message.message_id}")
            else:
                # Сообщение слишком длинное - разбиваем на части
                logger.info(f"⚠️ Сообщение слишком длинное ({len(cleaned_text)} символов), разбиваем на части")
                
                # Разбиваем дайджест на части по новостям
                parts = self.morning_digest_service._split_message_by_news(new_digest, max_length)
                
                # Список для хранения ID всех новых сообщений дайджеста
                new_message_ids = []
                
                # Отправляем каждую часть отдельно
                for i, part in enumerate(parts):
                    # Создаем временный дайджест только для новостей этой части
                    part_news_items = [new_digest.news_items[idx] for idx in part['news_indices']]
                    from src.services.morning_digest_service import MorningDigest
                    part_temp_digest = MorningDigest(
                        date=new_digest.date,
                        news_count=len(part_news_items), 
                        news_items=part_news_items,
                        curator_id=None
                    )
                    
                    # Используем метод для создания кнопок:
                    _, part_buttons = self.morning_digest_service.create_interactive_digest_message(part_temp_digest)
                    
                    # Убираем кнопку одобрения для не-последних частей
                    if i != len(parts) - 1:
                        part_buttons.pop()  # Удаляем последнюю кнопку "Одобрить оставшиеся"
                    
                    # Проверяем длину части перед отправкой
                    part_text = part['text']
                    if len(part_text) > config.telegram.max_message_length:
                        logger.warning(f"⚠️ Часть всё ещё слишком длинная: {len(part_text)} символов, обрезаем")
                        part_text = part_text[:config.telegram.max_message_length - 6] + "\n..."
                    
                    # Отправляем часть с кнопками
                    if part_buttons:
                        from telegram import InlineKeyboardMarkup
                        reply_markup = InlineKeyboardMarkup(part_buttons)
                        message = await query.message.chat.send_message(
                            text=part_text,
                            reply_markup=reply_markup,
                            parse_mode="HTML"
                        )
                        new_message_ids.append(message.message_id)
                    else:
                        # Отправляем без кнопок
                        message = await query.message.chat.send_message(text=part_text, parse_mode="HTML")
                        new_message_ids.append(message.message_id)
                
                # ВАЖНО: Сохраняем новые ID сообщений в сессию
                if new_message_ids:
                    self.morning_digest_service._save_digest_session(
                        str(query.message.chat.id), 
                        new_message_ids, 
                        new_digest.news_count
                    )
                    logger.info(f"💾 Обновлена сессия с новыми ID сообщений: {new_message_ids}")
            
            logger.info(f"✅ Новый дайджест создан и отправлен с {len(digest_news)} новостями")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания нового дайджеста: {e}")
            await query.answer("❌ Ошибка создания нового дайджеста")
    
    async def _handle_select_expert(self, query, user_id: int, expert_id: int):
        """Обработка выбора эксперта."""
        try:
            logger.info(f"👨‍💼 Обрабатываем выбор эксперта {expert_id} для пользователя {user_id}")
            
            if not await BotUtils.check_service_availability_simple(
                self.expert_choice_service, 
                "ExpertChoiceService", 
                query
            ):
                return
            
            expert = self.expert_choice_service.get_expert_by_id(expert_id)
            logger.info(f"👨‍💼 Получен эксперт: {expert}")
            
            if not expert:
                logger.error("❌ Эксперт не найден")
                await query.answer("❌ Эксперт не найден")
                return
            
            logger.info(f"👨‍💼 Эксперт найден: {expert.name}")
            
            # Сохраняем выбранного эксперта как эксперта недели
            logger.info(f"👨‍💼 Сохраняем эксперта {expert.name} как эксперта недели")
            self.service.set_expert_of_week(expert.id)
            
            # Отправляем новости эксперту
            logger.info(f"👨‍💼 Отправляем новости эксперту {expert.name}")
            await self._send_news_to_expert(query, expert, user_id)
                
        except Exception as e:
            logger.error(f"❌ Ошибка при выборе эксперта: {e}")
            await query.answer("❌ Произошла ошибка")
    
    async def _send_news_to_expert(self, query, expert, user_id: int):
        """Отправляет одобренные новости эксперту в личку."""
        try:
            logger.info(f"📤 Начинаем отправку новостей эксперту {expert.name} (ID: {expert.id})")
            
            # Проверяем доступность сервисов
            if not await BotUtils.check_service_availability_simple(
                self.interactive_moderation_service, 
                "InteractiveModerationService", 
                query
            ):
                return
            
            if not await BotUtils.check_service_availability_simple(
                self.expert_interaction_service, 
                "ExpertInteractionService", 
                query
            ):
                return
            
            # Получаем одобренные новости из сессии
            approved_news = await self.interactive_moderation_service.get_remaining_news(user_id)
            logger.info(f"📰 Получены одобренные новости: {len(approved_news)} штук")
            
            if not approved_news:
                logger.warning("⚠️ Нет одобренных новостей для отправки")
                await query.answer("❌ Нет одобренных новостей для отправки")
                return
            
            # Определяем ID эксперта для отправки
            try:
                # Пробуем преобразовать telegram_id в число
                expert_telegram_id = int(expert.telegram_id)
                expert_name = expert.name
                logger.info(f"👨‍💼 Эксперт: {expert_name}, Telegram ID: {expert_telegram_id}")
            except ValueError:
                # Если telegram_id не числовой, это username - пока не поддерживается
                logger.info(f"⚠️ Эксперт {expert.name} имеет username ({expert.telegram_id}) вместо числового ID")
                await query.answer("⚠️ Этот эксперт пока не подключен (нужен числовой Telegram ID)")
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
                    await self.interactive_moderation_service.cleanup_moderation_session(user_id)
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
            if not await BotUtils.check_service_availability_simple(
                self.expert_interaction_service, 
                "ExpertInteractionService", 
                query
            ):
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
    
    async def _handle_show_full_digest(self, query, user_id: int):
        """Показывает полный дайджест по запросу."""
        try:
            chat_id = str(query.message.chat.id)
            
            # Получаем сохраненный дайджест из сессии
            session = self.morning_digest_service.get_digest_session(chat_id)
            if not session or 'digest_data' not in session:
                await query.message.reply_text("❌ Сессия дайджеста не найдена")
                return
            
            digest = session['digest_data']
            
            # Создаем полный дайджест в сбалансированных частях
            parts = self.morning_digest_service._create_balanced_parts(digest, max_parts=config.message.max_digest_parts)
            
            for i, part in enumerate(parts, 1):
                await query.message.reply_text(
                    f"📄 <b>Часть {i}/{len(parts)}</b>\n\n{part['text']}",
                    reply_markup=InlineKeyboardMarkup(part.get('buttons', [])),
                    parse_mode="HTML"
                )
            
            await query.answer("📖 Показан полный дайджест")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при показе полного дайджеста: {e}")
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
        
        # ✅ Проверяем состояние ожидания правок в БД
        digest_edit_session = await self.session_service.get_session_data(
            session_type='digest_edit',
            user_id=str(user.id)
        )
        if digest_edit_session and digest_edit_session.get('waiting'):
            logger.info(f"📝 Получены правки дайджеста от пользователя {user.id}")
            await self._handle_digest_edit_message(update, user.id, text)
            return
        
        # ✅ Проверяем состояние ожидания фото в БД (старый формат)
        photo_waiting_session = await self.session_service.get_session_data(
            session_type='photo_waiting',
            user_id=str(user.id)
        )
        
        logger.info(f"🔍 Проверка фото: user.id={user.id}, photo_waiting={photo_waiting_session is not None}, has_photo={bool(update.message.photo)}")
        
        # Обработка фото для публикации
        if photo_waiting_session and update.message.photo:
            logger.info(f"📸 Получено фото для публикации от пользователя {user.id}")
            await self._handle_photo_for_publication(update, user.id)
            return
        
        # Проверяем, является ли пользователь экспертом с активной сессией
        if hasattr(self, 'expert_interaction_service') and self.expert_interaction_service:
            # Проверяем, есть ли активная сессия эксперта в БД
            expert_session = await self.session_service.get_session_data(
                session_type='expert_session',
                user_id=str(user.id)
            )
            if expert_session:
                # Это комментарий эксперта - обрабатываем его
                await self._handle_expert_comment(update, user.id, text)
                return
    
    async def _handle_expert_comment(self, update: Update, expert_id: int, comment_text: str):
        """Обрабатывает комментарий эксперта."""
        try:
            if not self.expert_interaction_service:
                await update.message.reply_text("❌ Сервис взаимодействия с экспертами недоступен")
                return
            
            # Получаем активную сессию эксперта из БД
            session_data = await self.session_service.get_session_data(
                session_type='expert_session',
                user_id=str(expert_id)
            )
            if not session_data:
                await update.message.reply_text("❌ Активная сессия не найдена")
                return
            
            # Определяем, к какой новости относится комментарий
            # Берем новость, которую эксперт выбрал для комментирования
            if not session_data.get('selected_news_id'):
                await update.message.reply_text("❌ Не выбрана новость для комментирования")
                return
            
            news_id = session_data['selected_news_id']
            
            # Проверяем, что новость еще не прокомментирована
            commented_news = session_data.get('commented_news', [])
            if news_id in commented_news:
                await update.message.reply_text("✅ Эта новость уже прокомментирована!")
                return
            
            # Сохраняем комментарий
            success = await self.expert_interaction_service.save_comment(expert_id, news_id, comment_text)
            
            if success:
                # Если есть еще новости для комментирования, показываем обновленный список
                commented_news = set(session_data.get('commented_news', []))
                news_ids = set(session_data.get('news_ids', []))
                if len(commented_news) < len(news_ids):
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
            if not self.expert_interaction_service:
                return
            
            # Получаем сессию эксперта из БД
            session_data = await self.session_service.get_session_data(
                session_type='expert_session',
                user_id=str(expert_id)
            )
            if not session_data:
                return
            
            # Получаем оставшиеся новости
            news_ids = set(session_data.get('news_ids', []))
            commented_news = set(session_data.get('commented_news', []))
            remaining_news_ids = news_ids - commented_news
            
            if not remaining_news_ids:
                return
            
            # Получаем реальные данные оставшихся новостей из сессии эксперта
            remaining_news = []
            news_items = session_data.get('news_items', [])
            for news in news_items:
                if news['id'] in remaining_news_ids:
                    remaining_news.append(news)
            
            if not remaining_news:
                logger.warning(f"⚠️ Не найдены данные для оставшихся новостей эксперта {expert_id}")
                return
            
            # Отправляем обновленный список (разбитый на части)
            news_parts = self.expert_interaction_service._split_news_list_for_expert(remaining_news)
            
            for i, part in enumerate(news_parts):
                keyboard = self.expert_interaction_service._create_comment_buttons_for_part(part['news_indices'], remaining_news)
                
                await self.application.bot.send_message(
                    chat_id=expert_id,
                    text=part['text'],
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="HTML"
                )
                
                # Небольшая задержка между сообщениями
                if i < len(news_parts) - 1:
                    await asyncio.sleep(config.timeout.message_delay_seconds)
            
            logger.info(f"✅ Обновленный список новостей отправлен эксперту {expert_id}: {len(remaining_news)} новостей")
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа обновленного списка новостей эксперту {expert_id}: {e}")
    
    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================
    
    
    
    
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
            response += f"🕐 Время отправки: {config.scheduler.morning_digest_hour}:00 утра\n"
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
            
            # ✅ Восстанавливаем активные сессии после запуска
            await self.restore_sessions_on_startup()
            
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
                await asyncio.sleep(config.timeout.bot_loop_sleep_seconds)
            
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
            
            if not await BotUtils.check_service_availability_simple(
                self.interactive_moderation_service, 
                "InteractiveModerationService", 
                query
            ):
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
            approved_news = await self.interactive_moderation_service.complete_moderation(user_id)
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
            expert_comments = await self.service.get_expert_comments_for_news([news.id for news in approved_news])
            
            # 4. Получаем источники новостей
            news_sources = self.service.get_news_sources([news.id for news in approved_news])
            
            logger.info(f"🔍 Отладка источников для финального дайджеста: {news_sources}")
            logger.info(f"📊 Получено {len(approved_news)} новостей, эксперт: {expert_of_week.name}, комментариев: {len(expert_comments)}")
            
            # Создаем финальный дайджест
            formatted_digest = await self.final_digest_formatter.create_final_digest(
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
            
            # ✅ Устанавливаем состояние ожидания правок в БД
            await self.session_service.save_session(
                session_type='digest_edit',
                user_id=str(user_id),
                data={'waiting': True, 'user_id': user_id},
                expires_at=datetime.now() + timedelta(seconds=config.timeout.approval_timeout)
            )
            logger.info(f"🔄 Установлено состояние ожидания правок в БД для пользователя {user_id}")
            
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
                # ✅ Убираем состояние ожидания правок из БД
                await self.session_service.delete_session(
                    session_type='digest_edit',
                    user_id=str(user_id)
                )
                logger.info(f"🔄 Снято состояние ожидания правок из БД для пользователя {user_id}")
                
                await update.message.reply_text("✅ Правки обработаны! Исправленный дайджест отправлен на согласование.")
            else:
                await update.message.reply_text(f"❌ Ошибка обработки правок: {result['error']}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки правок дайджеста: {e}")
            await update.message.reply_text("❌ Произошла ошибка при обработке правок")
    
    async def _handle_photo_for_publication(self, update: Update, user_id: int):
        """Обработка фото для публикации дайджеста через User API."""
        try:
            logger.info(f"📸 Обработка фото для публикации от пользователя {user_id}")
            
            # ✅ Получаем digest_text из БД
            photo_session = await self.session_service.get_session_data(
                session_type='photo_waiting',
                user_id=str(user_id)
            )
            if not photo_session:
                await update.message.reply_text("❌ Ошибка: не найден текст дайджеста для публикации")
                return
            
            digest_text = photo_session.get('digest_text')
            if not digest_text:
                await update.message.reply_text("❌ Ошибка: текст дайджеста поврежден")
                return
            
            # Получаем file_id самого большого фото
            photo = update.message.photo[-1]  # Берем фото с наивысшим разрешением
            photo_file_id = photo.file_id
            
            logger.info(f"📸 Получено фото с file_id: {photo_file_id}")
            
            # Скачиваем фото для User API
            photo_path = f"temp_photo_{user_id}.jpg"
            try:
                photo_file = await self.application.bot.get_file(photo_file_id)
                await photo_file.download_to_drive(photo_path)
                logger.info(f"📥 Фото скачано: {photo_path}")
                
                # 🚀 НОВОЕ: Публикуем через User API вместо Bot API
                from src.services.telegram_user_publisher import TelegramUserPublisher
                
                user_publisher = TelegramUserPublisher()  # Использует session_name из config (теперь "2")
                
                # Публикуем с фото и полным текстом в подписи (до 4096 символов!)
                channel_id = config.telegram.channel_id
                message_url = await user_publisher.publish_digest(
                    channel_id=channel_id,
                    content=digest_text,  # ПОЛНЫЙ ТЕКСТ БЕЗ ОГРАНИЧЕНИЙ!
                    photo_path=photo_path
                )
                
                # Отключаемся от User API
                await user_publisher.disconnect()
                
                if message_url:
                    # ✅ Убираем состояние ожидания фото из БД
                    await self.session_service.delete_session(
                        session_type='photo_waiting',
                        user_id=str(user_id)
                    )
                    logger.info(f"🔄 Снято состояние ожидания фото из БД для пользователя {user_id}")
                    
                    await update.message.reply_text(
                        f"🎉 <b>Дайджест успешно опубликован через User API!</b>\n\n"
                        f"📸 Фото с полным текстом в подписи ({len(digest_text)} символов)\n"
                        f"🔗 Ссылка: {message_url}",
                        parse_mode="HTML"
                    )
                    logger.info(f"✅ Дайджест опубликован через User API: {message_url}")
                    
                else:
                    # Fallback на Bot API при ошибке User API
                    logger.warning("⚠️ User API не сработал, используем fallback на Bot API")
                    await self._fallback_bot_publication(digest_text, photo_file_id, channel_id, user_id, update)
                
            except Exception as e:
                logger.error(f"❌ Ошибка публикации через User API: {e}")
                # Fallback на Bot API при ошибке
                await self._fallback_bot_publication(digest_text, photo_file_id, config.telegram.channel_id, user_id, update)
                
            finally:
                # ВСЕГДА удаляем временный файл
                try:
                    import os
                    if os.path.exists(photo_path):
                        os.remove(photo_path)
                        logger.info(f"🗑️ Временный файл удален: {photo_path}")
                except Exception as cleanup_error:
                    logger.warning(f"⚠️ Не удалось удалить временный файл: {cleanup_error}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки фото для публикации: {e}")
            await update.message.reply_text("❌ Произошла ошибка при публикации дайджеста")
    
    async def _fallback_bot_publication(self, digest_text: str, photo_file_id: str, channel_id: str, user_id: int, update: Update):
        """Fallback публикация через Bot API при ошибке User API"""
        try:
            logger.info("🔄 Fallback: публикация через Bot API")
            
            # 1. Отправляем фото без подписи
            await self.application.bot.send_photo(
                chat_id=channel_id,
                photo=photo_file_id
            )
            logger.info(f"📸 Фото отправлено без подписи (Bot API)")
            
            # 2. Отправляем полный текст отдельным сообщением
            clean_text = self._remove_title_from_digest(digest_text)
            await self.application.bot.send_message(
                chat_id=channel_id,
                text=clean_text,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            logger.info(f"📝 Полный текст отправлен: {len(clean_text)} символов (Bot API)")
            
            # ✅ Убираем состояние ожидания фото из БД
            await self.session_service.delete_session(
                session_type='photo_waiting',
                user_id=str(user_id)
            )
            logger.info(f"🔄 Снято состояние ожидания фото из БД для пользователя {user_id}")
            
            await update.message.reply_text(
                "🎉 Дайджест опубликован через Bot API!\n"
                "⚠️ User API недоступен, использован резервный метод"
            )
            logger.info(f"✅ Дайджест опубликован через Bot API (fallback)")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка публикации (Bot API): {str(e)}")
            logger.error(f"❌ Ошибка fallback публикации: {e}")
    
    def _remove_title_from_digest(self, digest_text: str) -> str:
        """Удаляет заголовок из дайджеста, чтобы избежать дублирования."""
        try:
            lines = digest_text.split('\n')
            cleaned_lines = []
            
            for line in lines:
                line_stripped = line.strip()
                # Пропускаем строки с заголовком (содержат 🤖 и "ИИ меняет мир")
                if ('🤖' in line_stripped and 'ИИ меняет мир' in line_stripped):
                    continue
                # Пропускаем пустые строки в начале
                if not line_stripped and not cleaned_lines:
                    continue
                cleaned_lines.append(line)
            
            # Убираем лишние пустые строки в начале
            while cleaned_lines and not cleaned_lines[0].strip():
                cleaned_lines.pop(0)
            
            return '\n'.join(cleaned_lines)
            
        except Exception as e:
            logger.error(f"❌ Ошибка удаления заголовка: {e}")
            return digest_text
    
    
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
            
            # Отправляем новое сообщение в чат кураторов (не ответ на удаленное сообщение)
            await self.application.bot.send_message(
                chat_id=config.telegram.curator_chat_id,
                text=message_text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            
            logger.info(f"✅ Выбор эксперта показан для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа выбора эксперта: {e}")
            await query.answer("❌ Ошибка при выборе эксперта")
    
    async def restore_sessions_on_startup(self):
        """
        Восстанавливает активные сессии при запуске бота.
        Критически важно для устойчивости к перезапускам!
        """
        try:
            logger.info("🔄 Восстановление активных сессий при запуске...")
            
            # Получаем все активные сессии из БД
            active_sessions = await self.session_service.get_active_sessions()
            
            if not active_sessions:
                logger.info("📭 Активных сессий не найдено")
                return
            
            # ✅ ОПТИМИЗАЦИЯ: Восстанавливаем сессии асинхронно с таймаутами
            restored_count = 0
            tasks = []
            
            for session in active_sessions:
                session_type = session['session_type']
                user_id = session['user_id']
                chat_id = session['chat_id']
                data = session['data']
                
                logger.debug(f"🔄 Восстанавливаем сессию: {session_type} для пользователя {user_id}")
                
                # Создаем задачу для восстановления сессии
                task = self._restore_single_session(session)
                tasks.append(task)
            
            # Выполняем все задачи параллельно с таймаутом
            if tasks:
                try:
                    from src.utils.timeout_utils import with_timeout
                    results = await with_timeout(
                        asyncio.gather(*tasks, return_exceptions=True),
                        timeout_seconds=config.timeout.session_restore_timeout,  # Таймаут восстановления сессий
                        operation_name="восстановление сессий",
                        fallback_value=[]
                    )
                    
                    # Подсчитываем успешно восстановленные сессии
                    for result in results:
                        if isinstance(result, Exception):
                            logger.error(f"❌ Ошибка восстановления сессии: {result}")
                        else:
                            restored_count += 1
                            
                except Exception as e:
                    logger.error(f"❌ Ошибка параллельного восстановления сессий: {e}")
                    # Fallback: восстанавливаем по одной
                    for session in active_sessions:
                        try:
                            await self._restore_single_session(session)
                            restored_count += 1
                        except Exception as session_error:
                            logger.error(f"❌ Ошибка восстановления сессии {session['session_type']}: {session_error}")

            if restored_count > 0:
                logger.info(f"✅ Восстановлено {restored_count} активных сессий")
            else:
                logger.debug("ℹ️ Активных сессий для восстановления не найдено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка восстановления сессий: {e}")
    
    async def _restore_single_session(self, session: dict):
        """Восстанавливает одну сессию с обработкой ошибок."""
        try:
            session_type = session['session_type']
            
            if session_type == 'expert_session':
                await self._restore_expert_session(session)
            elif session_type == 'photo_waiting':
                await self._restore_photo_waiting_session(session)
            elif session_type == 'digest_edit':
                await self._restore_digest_edit_session(session)
            elif session_type == 'current_digest':
                await self._restore_current_digest_session(session)
            elif session_type == 'moderation_session':
                await self._restore_moderation_session(session)
            elif session_type == 'expert_comment':
                await self._restore_expert_comment_session(session)
            elif session_type == 'telegram_user_session':
                # Пропускаем сессии Telegram User API (это нормально)
                logger.debug(f"📝 Пропускаем сессию Telegram User API")
            else:
                logger.warning(f"⚠️ Неизвестный тип сессии: {session_type}")
    
        except Exception as e:
            logger.error(f"❌ Ошибка восстановления сессии {session.get('session_type', 'unknown')}: {e}")
            raise
    
    async def _restore_expert_session(self, session: dict):
        """Восстанавливает сессию эксперта."""
        try:
            expert_id = int(session['user_id'])
            data = session['data']
            
            # Уведомляем эксперта о восстановлении сессии
            await self.application.bot.send_message(
                chat_id=expert_id,
                text=f"""
🔄 **Сессия восстановлена после перезапуска**

👨‍💻 Ваша работа продолжается с того же места.
📰 Осталось прокомментировать: {len(data['news_ids']) - len(data['commented_news'])} новостей

💬 Продолжайте комментировать новости.
                """,
                parse_mode="HTML"
            )
            
            logger.info(f"✅ Сессия эксперта {expert_id} восстановлена")
            
        except Exception as e:
            logger.error(f"❌ Ошибка восстановления сессии эксперта: {e}")
    
    async def _restore_photo_waiting_session(self, session: dict):
        """Восстанавливает состояние ожидания фото."""
        try:
            user_id = int(session['user_id'])
            
            # Напоминаем куратору о необходимости отправить фото
            await self.application.bot.send_message(
                chat_id=user_id,
                text="""
📸 **Напоминание: ожидается фото для публикации**

🔄 После перезапуска бота ваш дайджест сохранен.
📤 Пожалуйста, отправьте фото для публикации в канал.
                """,
                parse_mode="HTML"
            )
            
            logger.info(f"✅ Состояние ожидания фото для пользователя {user_id} восстановлено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка восстановления состояния ожидания фото: {e}")
    
    async def _restore_digest_edit_session(self, session: dict):
        """Восстанавливает состояние ожидания правок."""
        try:
            user_id = int(session['user_id'])
            
            # Напоминаем куратору о необходимости отправить правки
            await self.application.bot.send_message(
                chat_id=user_id,
                text="""
📝 **Напоминание: ожидаются правки дайджеста**

🔄 После перезапуска бота ваш запрос на редактирование сохранен.
✏️ Пожалуйста, отправьте исправленный текст дайджеста.
                """,
                parse_mode="HTML"
            )
            
            logger.info(f"✅ Состояние ожидания правок для пользователя {user_id} восстановлено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка восстановления состояния ожидания правок: {e}")
    
    async def _restore_current_digest_session(self, session: dict):
        """Восстанавливает текущий дайджест."""
        try:
            chat_id = session['chat_id']
            data = session['data']
            digest_length = len(data.get('digest_text', ''))
            
            logger.info(f"✅ Текущий дайджест для чата {chat_id} восстановлен ({digest_length} символов)")
            
        except Exception as e:
            logger.error(f"❌ Ошибка восстановления текущего дайджеста: {e}")
    
    async def _restore_moderation_session(self, session: dict):
        """Восстанавливает сессию модерации."""
        try:
            user_id = int(session['user_id'])
            data = session['data']
            
            # Уведомляем куратора о восстановлении сессии модерации
            remaining_count = len(data['news_items']) - len(data['removed_news'])
            
            await self.application.bot.send_message(
                chat_id=user_id,
                text=f"""
🔄 **Сессия модерации восстановлена**

📝 После перезапуска бота ваша модерация продолжается.
📰 Осталось новостей для модерации: {remaining_count}

🗑️ Продолжайте удалять ненужные новости кнопками.
✅ Затем нажмите "Одобрить оставшиеся".
                """,
                parse_mode="HTML"
            )
            
            logger.info(f"✅ Сессия модерации для пользователя {user_id} восстановлена")
            
        except Exception as e:
            logger.error(f"❌ Ошибка восстановления сессии модерации: {e}")
    
    async def _restore_expert_comment_session(self, session: dict):
        """Восстанавливает сессию комментария эксперта."""
        try:
            expert_id = int(session['user_id'])
            data = session['data']
            
            # Пробуем уведомить эксперта о восстановлении сессии комментария
            try:
                await self.application.bot.send_message(
                    chat_id=expert_id,
                    text=f"""
🔄 **Сессия комментария восстановлена**

💬 Ваш комментарий к новости сохранен и будет учтен.
📰 Новость: {data.get('news_title', 'Неизвестная новость')}

✅ Комментарий успешно добавлен в дайджест.
                    """,
                    parse_mode="HTML"
                )
                logger.info(f"✅ Сессия комментария эксперта {expert_id} восстановлена")
            except Exception as send_error:
                # Если чат не найден, просто пропускаем (это нормально для старых сессий)
                logger.debug(f"📝 Сессия комментария эксперта {expert_id}: чат недоступен, пропускаем")
            
        except Exception as e:
            logger.error(f"❌ Ошибка восстановления сессии комментария эксперта: {e}")


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