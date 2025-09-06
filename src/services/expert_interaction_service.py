#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Expert Interaction Service - сервис для взаимодействия с экспертами.
Включает отправку новостей, получение комментариев и систему напоминаний.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

@dataclass
class ExpertComment:
    """Комментарий эксперта к новости."""
    news_id: int
    comment: str
    timestamp: datetime
    expert_id: int

@dataclass
class ExpertSession:
    """Сессия работы эксперта с новостями."""
    expert_id: int
    news_ids: Set[int]  # ID новостей для комментирования
    commented_news: Set[int]  # ID прокомментированных новостей
    start_time: datetime
    last_reminder: datetime
    reminder_count: int = 0
    news_items: List[Dict] = None  # Полные данные новостей для отображения
    selected_news_id: int = None # ID выбранной новости для комментирования
    message_ids: List[int] = None  # ID сообщений с новостями для удаления

class ExpertInteractionService:
    """
    Сервис для взаимодействия с экспертами.
    """
    
    def __init__(self, bot: Bot, curator_approval_service=None):
        """
        Инициализация сервиса.
        
        Args:
            bot: Экземпляр Telegram бота
            curator_approval_service: Сервис согласования с кураторами
        """
        self.bot = bot
        self.curator_approval_service = curator_approval_service
        self.active_sessions: Dict[int, ExpertSession] = {}  # expert_id -> session
        self.comments: List[ExpertComment] = []  # Хранение в памяти
        
        # Настройки напоминаний
        self.REMINDER_INTERVAL = 3600  # 1 час в секундах
        self.CURATOR_ALERT_THRESHOLD = 14400  # 4 часа в секундах
        
        logger.info("✅ ExpertInteractionService инициализирован")
        if curator_approval_service:
            logger.info("✅ CuratorApprovalService передан в ExpertInteractionService")
    
    def _clean_html_text(self, text: str) -> str:
        """
        Очищает текст от неправильных HTML тегов, сохраняя полезное форматирование.
        
        Args:
            text: Исходный текст
            
        Returns:
            str: Очищенный текст
        """
        import re
        
        # Разрешенные HTML теги для Telegram (HTML parse_mode)
        allowed_tags = ['b', 'i', 'u', 's', 'code', 'pre', 'a', 'br', 'p']
        
        # Удаляем все теги, кроме разрешенных
        # Это более безопасный подход, чем попытка исправить каждый неправильный тег
        # Сначала удаляем теги с атрибутами, оставляя только чистые теги
        for tag in allowed_tags:
            text = re.sub(f'<{tag}[^>]*>', f'<{tag}>', text)
            text = re.sub(f'</{tag}[^>]*>', f'</{tag}>', text)
        
        # Удаляем все остальные теги, которые не входят в allowed_tags
        text = re.sub(r'<(?!/?(?:' + '|'.join(allowed_tags) + '))[^>]*>', '', text)
        
        # Удаляем теги, которые содержат цифры и буквы (например, "500m.")
        text = re.sub(r'<[^>]*[0-9]+[a-zA-Z]*[^>]*>', '', text)
        
        # Удаляем теги с неправильными символами
        text = re.sub(r'<[^>]*[^a-zA-Z0-9\s/<>][^>]*>', '', text)
        
        # Удаляем пустые теги
        text = re.sub(r'<[^>]*></[^>]*>', '', text)
        
        # Удаляем незакрытые теги в конце строки
        text = re.sub(r'<[^>]*$', '', text)
        
        # Удаляем множественные пробелы
        text = re.sub(r'\s+', ' ', text)
        
        # Удаляем пробелы в начале и конце
        text = text.strip()
        
        return text
    
    async def send_news_to_expert(self, expert_id: int, news_items: List[Dict], expert_name: str) -> bool:
        """
        Отправляет новости эксперту для комментирования.
        
        Args:
            expert_id: ID эксперта
            news_items: Список новостей
            expert_name: Имя эксперта
            
        Returns:
            bool: True если отправка успешна
        """
        try:
            # Создаем сессию для эксперта
            news_ids = {news['id'] for news in news_items}
            session = ExpertSession(
                expert_id=expert_id,
                news_ids=news_ids,
                commented_news=set(),
                start_time=datetime.now(),
                last_reminder=datetime.now(),
                message_ids=[]
            )
            
            # Сохраняем полные данные новостей для отображения
            session.news_items = news_items
            
            self.active_sessions[expert_id] = session
            
            # Отправляем приветственное сообщение
            welcome_text = self._create_welcome_message(expert_name)
            await self.bot.send_message(
                chat_id=expert_id,
                text=welcome_text,
                parse_mode="HTML"
            )
            
            # Отправляем список новостей с кнопками (разбитый на части)
            news_parts = self._split_news_list_for_expert(news_items)
            
            if len(news_parts) == 1:
                # Если только одна часть, отправляем как раньше
                news_text = news_parts[0]['text']
                keyboard = self._create_comment_buttons_for_part(news_parts[0]['news_indices'], news_items)
                
                message = await self.bot.send_message(
                    chat_id=expert_id,
                    text=news_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="HTML"
                )
                session.message_ids.append(message.message_id)
            else:
                # Если несколько частей, отправляем каждую отдельно
                for i, part in enumerate(news_parts):
                    keyboard = self._create_comment_buttons_for_part(part['news_indices'], news_items)
                    
                    message = await self.bot.send_message(
                        chat_id=expert_id,
                        text=part['text'],
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode="HTML"
                    )
                    session.message_ids.append(message.message_id)
                    
                    # Небольшая задержка между сообщениями
                    await asyncio.sleep(0.5)
            
            # Запускаем систему напоминаний
            asyncio.create_task(self._start_reminder_system(expert_id))
            
            logger.info(f"✅ Новости отправлены эксперту {expert_name} (ID: {expert_id})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки новостей эксперту {expert_id}: {e}")
            return False
    
    def _create_welcome_message(self, expert_name: str) -> str:
        """Создает приветственное сообщение с ТЗ."""
        return f"""
🎯 <b>Добро пожаловать, {expert_name}!</b>

Вас выбрали <b>экспертом дня</b> для анализа новостей в сфере ИИ.

📋 <b>ТЗ для комментария:</b>

• <b>Объем:</b> 2-4 предложения (50-80 слов)
• <b>Стиль:</b> Профессиональный, но доступный для широкой аудитории
• <b>Без жаргонов</b>

<b>Комментарий должен содержать:</b>
✅ Оценку значимости новости (например: "Это важный шаг для развития ИИ в игровой аудитории")
✅ Анализ потенциального влияния (например: "Это может изменить подход к разработке игр")
❌ Никаких личных историй или отвлечений от темы

Готовы приступить к анализу? 🚀
"""
    
    def _create_news_list(self, news_items: List[Dict]) -> str:
        """Создает список новостей для эксперта."""
        news_text = "📰 <b>Новости для комментирования:</b>\n\n"
        
        for i, news in enumerate(news_items, 1):
            title = news.get('title', 'Без заголовка')
            summary = news.get('summary', 'Без описания')
            source = news.get('source_links', 'Не указан')
            
            # ПОЛНЫЙ ФОРМАТ без ограничений длины
            news_text += f"""
<b>{i}. {title}</b>
📝 {summary}
➡️ Источник: {source}

"""
        
        return news_text
    
    def _split_news_list_for_expert(self, news_items: List[Dict], max_length: int = 3500) -> List[Dict]:
        """
        Разбивает список новостей на части для эксперта.
        
        Args:
            news_items: Список новостей
            max_length: Максимальная длина части
            
        Returns:
            List[Dict]: Список частей с новостями и кнопками
        """
        if not news_items:
            return []
        
        parts = []
        current_part = "📰 <b>Новости для комментирования:</b>\n\n"
        current_news = []
        current_buttons = []
        
        for i, news in enumerate(news_items, 1):
            title = self._clean_html_text(news.get('title', 'Без заголовка'))
            summary = self._clean_html_text(news.get('summary', 'Без описания'))
            source = self._clean_html_text(news.get('source_links', 'Не указан'))
            
            news_text = f"""
<b>{i}. {title}</b>
📝 {summary}
➡️ Источник: {source}

"""
            
            # Проверяем, не превысит ли добавление новости лимит
            if len(current_part + news_text) > max_length and current_part != "📰 <b>Новости для комментирования:</b>\n\n":
                # Сохраняем текущую часть
                parts.append({
                    'text': current_part,
                    'news_indices': current_news,
                    'buttons': current_buttons
                })
                
                # Начинаем новую часть
                current_part = "📰 <b>Новости для комментирования:</b>\n\n" + news_text
                current_news = [i-1]
                current_buttons = [i-1]
            else:
                # Добавляем новость к текущей части
                current_part += news_text
                current_news.append(i-1)
                current_buttons.append(i-1)
        
        # Добавляем последнюю часть
        if current_part and current_part != "📰 <b>Новости для комментирования:</b>\n\n":
            parts.append({
                'text': current_part,
                'news_indices': current_news,
                'buttons': current_buttons
            })
        
        return parts
    
    def _create_comment_buttons(self, news_items: List[Dict]) -> List[List[InlineKeyboardButton]]:
        """Создает кнопки для комментирования каждой новости."""
        buttons = []
        
        for i, news in enumerate(news_items, 1):
            button = InlineKeyboardButton(
                f"💬 Прокомментировать новость {i}",
                callback_data=f"comment_news_{news['id']}"
            )
            buttons.append([button])
        
        return buttons
    
    def _create_comment_buttons_for_part(self, news_indices: List[int], all_news_items: List[Dict]) -> List[List[InlineKeyboardButton]]:
        """
        Создает кнопки для комментирования новостей в конкретной части.
        
        Args:
            news_indices: Индексы новостей в этой части
            all_news_items: Все новости
            
        Returns:
            List[List[InlineKeyboardButton]]: Кнопки для части
        """
        buttons = []
        
        for news_idx in news_indices:
            if 0 <= news_idx < len(all_news_items):
                news = all_news_items[news_idx]
                # Номер новости в общем списке (начиная с 1)
                news_number = news_idx + 1
                button = InlineKeyboardButton(
                    f"💬 Прокомментировать новость {news_number}",
                    callback_data=f"comment_news_{news['id']}"
                )
                buttons.append([button])
        
        return buttons
    
    async def handle_comment_request(self, expert_id: int, news_id: int) -> str:
        """
        Обрабатывает запрос на комментирование новости.
        
        Args:
            expert_id: ID эксперта
            news_id: ID новости
            
        Returns:
            str: Сообщение для эксперта
        """
        session = self.active_sessions.get(expert_id)
        if not session:
            return "❌ Сессия не найдена. Обратитесь к кураторам."
        
        if news_id not in session.news_ids:
            return "❌ Новость не найдена в списке для комментирования."
        
        if news_id in session.commented_news:
            return "✅ Эта новость уже прокомментирована."
        
        # Сохраняем выбранную новость в сессии
        session.selected_news_id = news_id
        
        # Находим выбранную новость
        selected_news = None
        for news in session.news_items:
            if news['id'] == news_id:
                selected_news = news
                break
        
        if not selected_news:
            return "❌ Данные новости не найдены."
        
        # Удаляем все сообщения с новостями (кроме текущего)
        await self._delete_news_messages(expert_id)
        
        # Формируем сообщение с новостью и ТЗ
        message = f"""
💬 <b>КОММЕНТИРУЕМ НОВОСТЬ:</b>

<b>📰 {selected_news.get('title', 'Без заголовка')}</b>
📝 {selected_news.get('summary', 'Без описания')}
➡️ Источник: {selected_news.get('source_links', 'Не указан')}

<b>📋 ТЗ ДЛЯ КОММЕНТАРИЯ:</b>
• 2-4 предложения (50-80 слов)
• Профессиональный, но доступный стиль
• Оценка значимости + анализ влияния
• Без личных историй

<b>💬 Напишите ваш комментарий в следующем сообщении:</b>
"""
        
        return message
    
    async def _delete_news_messages(self, expert_id: int):
        """Удаляет все сообщения с новостями для эксперта."""
        try:
            session = self.active_sessions.get(expert_id)
            if not session or not hasattr(session, 'message_ids'):
                return
            
            # Удаляем все сообщения с новостями
            for message_id in session.message_ids:
                try:
                    await self.bot.delete_message(
                        chat_id=expert_id,
                        message_id=message_id
                    )
                    logger.info(f"🗑️ Удалено сообщение с новостями: {message_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось удалить сообщение {message_id}: {e}")
            
            # Очищаем список ID сообщений
            session.message_ids = []
            
        except Exception as e:
            logger.error(f"❌ Ошибка удаления сообщений с новостями: {e}")
    
    async def save_comment(self, expert_id: int, news_id: int, comment_text: str) -> bool:
        """
        Сохраняет комментарий эксперта.
        
        Args:
            expert_id: ID эксперта
            news_id: ID новости
            comment_text: Текст комментария
            
        Returns:
            bool: True если комментарий сохранен
        """
        try:
            session = self.active_sessions.get(expert_id)
            if not session:
                logger.error(f"❌ Сессия не найдена для эксперта {expert_id}")
                return False
            
            # Сохраняем комментарий в памяти
            comment = ExpertComment(
                news_id=news_id,
                comment=comment_text,
                timestamp=datetime.now(),
                expert_id=expert_id
            )
            self.comments.append(comment)
            
            # Сохраняем комментарий в базу данных
            try:
                from models.database import Comment, Expert
                from services.postgresql_database_service import PostgreSQLDatabaseService
                
                db_service = PostgreSQLDatabaseService()
                with db_service.get_session() as db_session:
                    # Находим эксперта по Telegram ID (expert_id это telegram_id в данном контексте)
                    expert = db_session.query(Expert).filter(Expert.telegram_id == str(expert_id)).first()
                    if not expert:
                        logger.error(f"❌ Эксперт с Telegram ID {expert_id} не найден в БД")
                        return False
                    
                    logger.info(f"✅ Найден эксперт в БД: {expert.name} (ID: {expert.id}, Telegram ID: {expert.telegram_id})")
                    
                    # Создаем комментарий в БД
                    db_comment = Comment(
                        text=comment_text,
                        news_id=news_id,
                        expert_id=expert.id,  # Используем expert.id из БД, а не telegram_id
                        created_at=datetime.now()
                    )
                    
                    db_session.add(db_comment)
                    db_session.commit()
                    logger.info(f"✅ Комментарий сохранен в БД: эксперт {expert_id}, новость {news_id}")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка сохранения комментария в БД: {e}")
                # Продолжаем работу даже если БД недоступна
            
            # Отмечаем новость как прокомментированную
            session.commented_news.add(news_id)
            
            logger.info(f"✅ Комментарий сохранен: эксперт {expert_id}, новость {news_id}")
            
            # Проверяем, завершена ли работа эксперта
            if self._is_expert_work_completed(expert_id):
                await self._notify_expert_completion(expert_id)
                # Уведомляем кураторов и создаем финальный дайджест
                await self._notify_curators_completion(expert_id)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения комментария: {e}")
            return False
    
    def _is_expert_work_completed(self, expert_id: int) -> bool:
        """Проверяет, завершил ли эксперт работу."""
        session = self.active_sessions.get(expert_id)
        if not session:
            return False
        
        return len(session.commented_news) == len(session.news_ids)
    
    async def _notify_expert_completion(self, expert_id: int):
        """Уведомляет эксперта о завершении работы."""
        try:
            completion_text = """
🎉 <b>Отлично! Работа завершена!</b>

Вы прокомментировали все новости. Спасибо за ваше внимание и профессиональный анализ!

📊 Ваши комментарии переданы кураторам для формирования финального дайджеста.

До новых встреч! 👋
"""
            
            await self.bot.send_message(
                chat_id=expert_id,
                text=completion_text,
                parse_mode="HTML"
            )
            
            # Уведомляем кураторов и создаем финальный дайджест
            await self._notify_curators_completion(expert_id)
            
            # Очищаем сессию
            if expert_id in self.active_sessions:
                del self.active_sessions[expert_id]
            
            logger.info(f"✅ Эксперт {expert_id} уведомлен о завершении работы")
            
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления эксперта {expert_id}: {e}")
    
    async def _notify_curators_completion(self, expert_id: int):
        """Уведомляет кураторов о завершении работы эксперта и создает финальный дайджест."""
        try:
            # ID чата кураторов
            curators_chat_id = "-1002983482030"
            
            session = self.active_sessions.get(expert_id)
            if not session:
                return
            
            # Получаем имя эксперта (пока заглушка)
            expert_name = f"Эксперт {expert_id}"
            
            notification_text = f"""
✅ <b>Эксперт завершил работу!</b>

👨‍💻 <b>{expert_name}</b> прокомментировал все новости:
📊 Новостей: {len(session.news_ids)}
💬 Комментариев: {len(session.commented_news)}

🎨 <b>Создаем финальный дайджест...</b>
"""
            
            await self.bot.send_message(
                chat_id=curators_chat_id,
                text=notification_text,
                parse_mode="HTML"
            )
            
            logger.info(f"✅ Кураторы уведомлены о завершении работы эксперта {expert_id}")
            
            # Автоматически создаем финальный дайджест
            await self._create_final_digest_automatically(expert_id)
            
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления кураторов: {e}")
    
    async def _create_final_digest_automatically(self, expert_id: int):
        """Автоматически создает финальный дайджест после завершения работы эксперта."""
        try:
            logger.info(f"🎨 Автоматически создаем финальный дайджест для эксперта {expert_id}")
            
            # Импортируем необходимые сервисы
            from src.services.final_digest_formatter_service import FinalDigestFormatterService
            from src.services.curator_approval_service import CuratorApprovalService
            from src.services.bot_database_service import BotDatabaseService
            from src.services.ai_analysis_service import AIAnalysisService
            
            # Инициализируем сервисы
            ai_service = AIAnalysisService()  # ProxyAPI уже инициализируется в конструкторе
            formatter_service = FinalDigestFormatterService(ai_service)
            database_service = BotDatabaseService()
            
            # Получаем данные из текущей сессии эксперта
            session = self.active_sessions.get(expert_id)
            if not session:
                logger.error(f"❌ Сессия эксперта {expert_id} не найдена")
                return
            
            # Получаем новости, которые прокомментировал эксперт
            from models.database import News
            approved_news = []
            with database_service.db_service.get_session() as db_session:
                for news_id in session.news_ids:
                    news = db_session.query(News).filter(News.id == news_id).first()
                    if news:
                        approved_news.append(news)
            
            # Получаем эксперта недели
            expert_of_week = database_service.get_expert_of_week()
            
            # Получаем комментарии эксперта для этих новостей
            news_ids = [news.id for news in approved_news]
            expert_comments = database_service.get_expert_comments_for_news(news_ids)
            news_sources = database_service.get_news_sources(news_ids)
            
            logger.info(f"📊 Получено данных: {len(approved_news)} новостей, эксперт: {expert_of_week.name if expert_of_week else 'None'}")
            
            # Создаем финальный дайджест
            formatted_digest = formatter_service.create_final_digest(
                approved_news=approved_news,
                expert_of_week=expert_of_week,
                expert_comments=expert_comments,
                news_sources=news_sources
            )
            
            # Отправляем на согласование кураторам
            curator_chat_id = "-1002983482030"
            
            # Используем переданный CuratorApprovalService или создаем новый
            if self.curator_approval_service:
                logger.info("✅ Используем переданный CuratorApprovalService")
                approval_service = self.curator_approval_service
            else:
                logger.warning("⚠️ CuratorApprovalService не передан, создаем новый")
                # Получаем ссылку на бот из контекста
                bot_instance = None
                try:
                    import sys
                    from src.bot.bot import AINewsBot
                    
                    # Ищем в модуле bot.bot
                    bot_module = sys.modules.get('src.bot.bot') or sys.modules.get('bot.bot')
                    if bot_module and hasattr(bot_module, 'bot_instance'):
                        bot_instance = bot_module.bot_instance
                        logger.info(f"✅ Найден bot_instance для CuratorApprovalService")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось получить bot_instance: {e}")
                
                approval_service = CuratorApprovalService(
                    bot_token="8195833718:AAGbqnbZz7NrbOWN5ic5k7oxGMUTntgHE6s",
                    curator_chat_id=curator_chat_id,
                    formatter_service=formatter_service,
                    bot_instance=bot_instance
                )
            
            await approval_service.send_digest_for_approval(formatted_digest, curator_chat_id)
            
            logger.info(f"✅ Финальный дайджест автоматически создан и отправлен на согласование")
            
        except Exception as e:
            logger.error(f"❌ Ошибка автоматического создания финального дайджеста: {e}")
    
    async def _start_reminder_system(self, expert_id: int):
        """Запускает систему напоминаний для эксперта."""
        while expert_id in self.active_sessions:
            try:
                await asyncio.sleep(self.REMINDER_INTERVAL)
                
                session = self.active_sessions.get(expert_id)
                if not session:
                    break
                
                # Проверяем, не прошло ли 4 часа
                time_passed = (datetime.now() - session.start_time).total_seconds()
                
                if time_passed >= self.CURATOR_ALERT_THRESHOLD:
                    # Уведомляем кураторов
                    await self._alert_curators_about_unresponsive_expert(expert_id)
                    break
                else:
                    # Отправляем напоминание эксперту
                    await self._send_reminder_to_expert(expert_id)
                    session.reminder_count += 1
                    session.last_reminder = datetime.now()
                
            except Exception as e:
                logger.error(f"❌ Ошибка в системе напоминаний для эксперта {expert_id}: {e}")
                break
    
    async def _send_reminder_to_expert(self, expert_id: int):
        """Отправляет напоминание эксперту."""
        try:
            session = self.active_sessions.get(expert_id)
            if not session:
                return
            
            remaining_news = len(session.news_ids) - len(session.commented_news)
            
            reminder_text = f"""
⏰ <b>Напоминание!</b>

У вас осталось прокомментировать <b>{remaining_news}</b> новостей.

💡 Не забудьте ТЗ:
• 2-4 предложения
• Оценка значимости + анализ влияния
• Профессиональный стиль

Продолжайте работу! 🚀
"""
            
            await self.bot.send_message(
                chat_id=expert_id,
                text=reminder_text,
                parse_mode="HTML"
            )
            
            logger.info(f"✅ Напоминание отправлено эксперту {expert_id}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки напоминания эксперту {expert_id}: {e}")
    
    async def _alert_curators_about_unresponsive_expert(self, expert_id: int):
        """Уведомляет кураторов о неотзывчивом эксперте."""
        try:
            curators_chat_id = "-1002983482030"
            
            session = self.active_sessions.get(expert_id)
            if not session:
                return
            
            # Получаем имя эксперта (пока заглушка)
            expert_name = f"Эксперт {expert_id}"
            
            alert_text = f"""
⚠️ <b>ВНИМАНИЕ КУРАТОРАМ!</b>

👨‍💻 <b>{expert_name}</b> не отвечает уже <b>4+ часа</b>

📰 Новости ожидают комментариев:
{self._format_remaining_news_list(expert_id)}

🔔 <b>Пожалуйста, свяжитесь с экспертом лично:</b>
• Напишите в личку
• Позвоните по телефону
• Узнайте, нужна ли помощь

⏰ Время ожидания: {self._format_time_passed(session.start_time)}

🚨 Система автоматических напоминаний остановлена.
"""
            
            await self.bot.send_message(
                chat_id=curators_chat_id,
                text=alert_text,
                parse_mode="HTML"
            )
            
            logger.warning(f"🚨 Кураторы уведомлены о неотзывчивом эксперте {expert_id}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления кураторов о неотзывчивом эксперте: {e}")
    
    def _format_remaining_news_list(self, expert_id: int) -> str:
        """Форматирует список оставшихся новостей."""
        session = self.active_sessions.get(expert_id)
        if not session:
            return "Список недоступен"
        
        remaining = session.news_ids - session.commented_news
        if not remaining:
            return "Все новости прокомментированы"
        
        return f"Осталось: {len(remaining)} новостей"
    
    def _format_time_passed(self, start_time: datetime) -> str:
        """Форматирует прошедшее время."""
        time_passed = datetime.now() - start_time
        hours = int(time_passed.total_seconds() // 3600)
        minutes = int((time_passed.total_seconds() % 3600) // 60)
        
        if hours > 0:
            return f"{hours}ч {minutes}м"
        else:
            return f"{minutes}м"
    
    def get_expert_comments(self, expert_id: int) -> List[ExpertComment]:
        """Получает все комментарии эксперта."""
        return [comment for comment in self.comments if comment.expert_id == expert_id]
    
    def get_news_comments(self, news_id: int) -> List[ExpertComment]:
        """Получает все комментарии к новости."""
        return [comment for comment in self.comments if comment.news_id == news_id]
    
    def cleanup_session(self, expert_id: int):
        """Очищает сессию эксперта."""
        if expert_id in self.active_sessions:
            del self.active_sessions[expert_id]
            logger.info(f"🧹 Сессия эксперта {expert_id} очищена")

