#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Morning Digest Service - сервис для автоматической отправки утренних дайджестов.
Создает краткие саммари новостей за последние 24 часа и отправляет кураторам.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import asyncio
from telegram import InlineKeyboardButton
from src.config import config
from src.models import DigestSession, engine
from src.utils.message_splitter import MessageSplitter
from sqlalchemy.orm import Session as DBSession

logger = logging.getLogger(__name__)

@dataclass
class DigestNews:
    """Новость для дайджеста."""
    id: int
    title: str
    summary: str
    source_links: str
    published_at: datetime
    curator_id: Optional[str] = None

@dataclass
class MorningDigest:
    """Утренний дайджест."""
    date: datetime
    news_count: int
    news_items: List[DigestNews]
    curator_id: Optional[str] = None

class MorningDigestService:
    """
    Сервис для создания и отправки утренних дайджестов согласно ФТ.
    """
    
    def __init__(self, 
                 database_service,
                 ai_analysis_service,
                 curators_chat_id: str = None,
                 expert_selection_service=None,
                 bot=None):
        """
        Инициализация сервиса.
        
        Args:
            database_service: Сервис для работы с базой данных
            ai_analysis_service: Сервис AI анализа
            curator_service: Сервис кураторов
            expert_selection_service: Сервис выбора эксперта
            bot: Telegram bot для отправки сообщений
            curators_chat_id: ID чата кураторов
        """
        self.db = database_service
        self.database_service = database_service  # Добавляем алиас для совместимости
        self.ai_service = ai_analysis_service

        self.expert_selection_service = expert_selection_service
        self.bot = bot
        self.curators_chat_id = curators_chat_id or config.telegram.curator_chat_id
        
        # Система отслеживания ID сообщений дайджеста в базе данных
        # self.digest_sessions = {}  # Убираем словарь в памяти
        self.db_engine = engine  # Для работы с DigestSession
        
        logger.info(f"✅ MorningDigestService инициализирован (чат кураторов: {curators_chat_id})")
    
    # ============================================================================
    # НОВЫЕ МЕТОДЫ РАБОТЫ С БД (PostgreSQL DigestSession)
    # ============================================================================
    
    def _save_digest_session(self, chat_id: str, message_ids: List[int], news_count: int):
        """
        Сохраняет информацию о сессии дайджеста в PostgreSQL.
        
        Args:
            chat_id: ID чата
            message_ids: Список ID сообщений дайджеста
            news_count: Количество новостей в дайджесте
        """
        try:
            logger.info(f"💾 [БД] Сохраняем сессию дайджеста для чата: {chat_id} (тип: {type(chat_id)})")
            logger.info(f"💾 [БД] ID сообщений: {message_ids}")
            
            with DBSession(bind=self.db_engine) as session:
                # Проверяем, есть ли активная сессия для этого чата
                existing_session = session.query(DigestSession).filter(
                    DigestSession.chat_id == str(chat_id),
                    DigestSession.is_active == True
                ).first()
                
                if existing_session:
                    # Обновляем существующую сессию
                    existing_session.message_ids = json.dumps(message_ids)
                    existing_session.news_count = news_count
                    existing_session.updated_at = datetime.now()
                    logger.info(f"🔄 [БД] Обновлена существующая сессия ID={existing_session.id}")
                else:
                    # Создаем новую сессию
                    new_session = DigestSession(
                        chat_id=str(chat_id),
                        message_ids=json.dumps(message_ids),
                        news_count=news_count,
                        is_active=True
                    )
                    session.add(new_session)
                    logger.info(f"➕ [БД] Создана новая сессия")
                
                session.commit()
                logger.info(f"✅ [БД] Сессия сохранена для чата {chat_id}: {len(message_ids)} сообщений, {news_count} новостей")
                
        except Exception as e:
            logger.error(f"❌ [БД] Ошибка сохранения сессии дайджеста: {e}")
            raise e
    
    def get_digest_session(self, chat_id: str) -> Optional[Dict]:
        """
        Получает информацию о сессии дайджеста из PostgreSQL.
        
        Args:
            chat_id: ID чата
            
        Returns:
            Dict: Информация о сессии или None
        """
        try:
            logger.info(f"🔍 [БД] Ищем сессию дайджеста для чата: {chat_id}")
            
            with DBSession(bind=self.db_engine) as session:
                digest_session = session.query(DigestSession).filter(
                    DigestSession.chat_id == str(chat_id),
                    DigestSession.is_active == True
                ).first()
                
                if digest_session:
                    session_data = {
                        'chat_id': digest_session.chat_id,
                        'message_ids': json.loads(digest_session.message_ids),
                        'news_count': digest_session.news_count,
                        'created_at': digest_session.created_at,
                        'is_active': digest_session.is_active
                    }
                    logger.info(f"✅ [БД] Сессия найдена: {len(session_data['message_ids'])} сообщений")
                    return session_data
                else:
                    logger.warning(f"⚠️ [БД] Сессия не найдена для чата {chat_id}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ [БД] Ошибка получения сессии дайджеста: {e}")
            return None
    
    def clear_digest_session(self, chat_id: str):
        """
        Деактивирует сессию дайджеста для указанного чата в PostgreSQL.
        
        Args:
            chat_id: ID чата
        """
        try:
            logger.info(f"🗑️ [БД] Деактивируем сессию дайджеста для чата: {chat_id}")
            
            with DBSession(bind=self.db_engine) as session:
                digest_session = session.query(DigestSession).filter(
                    DigestSession.chat_id == str(chat_id),
                    DigestSession.is_active == True
                ).first()
                
                if digest_session:
                    digest_session.is_active = False
                    digest_session.updated_at = datetime.now()
                    session.commit()
                    logger.info(f"✅ [БД] Сессия деактивирована для чата {chat_id}")
                else:
                    logger.warning(f"⚠️ [БД] Активная сессия не найдена для чата {chat_id}")
                    
        except Exception as e:
            logger.error(f"❌ [БД] Ошибка деактивации сессии дайджеста: {e}")
    
    
    async def create_morning_digest(self, curator_id: Optional[str] = None) -> MorningDigest:
        """
        Создает утренний дайджест новостей за последние 24 часа.
        
        Args:
            curator_id: ID куратора (если None - для всех кураторов)
            
        Returns:
            MorningDigest: Готовый дайджест
        """
        try:
            logger.info("🌅 Создаем утренний дайджест...")
            
            # Получаем новости за последние 24 часа
            news_items = await self._get_recent_news(hours=config.timeout.news_parsing_interval * 24)
            
            if not news_items:
                logger.info("📭 Новостей за последние 24 часа не найдено")
                return self._create_empty_digest()
            
            # Создаем краткие саммари для каждой новости
            digest_news = []
            
            for news in news_items:
                # Создаем краткое саммари (используем AI или fallback)
                summary = await self._create_news_summary(news)
                
                # Сохраняем саммари в БД
                await self._save_summary_to_db(news.id, summary)

                source_links = news.source_url or "Источник не указан"
                logger.info(f"🔗 Источник для новости {news.id}: '{news.source_url}' -> '{source_links}'")
                
                # Создаем объект для дайджеста
                digest_item = DigestNews(
                    id=news.id,
                    title=news.title,
                    summary=summary,
                    source_links=source_links,
                    published_at=news.published_at or news.created_at,
                    curator_id=news.curator_id
                )
                
                # Логируем создание элемента дайджеста
                logger.info(f"📰 Создан элемент дайджеста: ID={news.id}, Title='{news.title[:50]}...'")
                    
                digest_news.append(digest_item)
            
            # Создаем дайджест
            digest = MorningDigest(
                date=datetime.now(),
                news_count=len(digest_news),
                news_items=digest_news,
                curator_id=curator_id
            )
            
            logger.info(f"✅ Дайджест создан: {digest.news_count} новостей")
            return digest
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания дайджеста: {e}")
            return self._create_empty_digest()
    
    async def _get_recent_news(self, hours: int = None) -> List[Any]:
        """
        Получает новости за последние N часов с AI-фильтрацией по релевантности.
        
        Args:
            hours: Количество часов для поиска (по умолчанию из конфигурации)
            
        Returns:
            List: Список отфильтрованных новостей
        """
        try:
            # Используем значение по умолчанию из конфигурации если не указано
            if hours is None:
                hours = config.timeout.news_parsing_interval * 24
            
            # Вычисляем время начала периода
            start_time = datetime.now() - timedelta(hours=hours)
            
            # Получаем реальные новости из базы данных
            if self.db:
                try:
                    # Получаем новости за последние N часов
                    recent_news = await self.db.get_news_since(start_time)
                    
                    if recent_news:
                        logger.info(f"📰 Найдено {len(recent_news)} реальных новостей за последние {hours} часов")
                        
                        # Фильтруем новости по релевантности
                        filtered_news = await self._filter_news_by_relevance(recent_news)
                        
                        logger.info(f"🔍 После AI-фильтрации осталось {len(filtered_news)} релевантных новостей")
                        return filtered_news
                    else:
                        logger.info(f"📰 Новости за последние {hours} часов не найдены")
                        return []
                        
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось получить новости из БД: {e}")
                    logger.info("📰 Используем fallback: пустой список новостей")
                    return []
            else:
                logger.warning("⚠️ Database service недоступен")
                return []
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения новостей: {e}")
            return []
    
    async def _filter_news_by_relevance(self, news_list: List[Any]) -> List[Any]:
        """
        Фильтрует новости по релевантности для ИИ-дайджеста.
        
        Args:
            news_list: Список новостей для фильтрации
            
        Returns:
            List: Отфильтрованный список новостей
        """
        try:
            if not news_list:
                return []
            
            logger.info(f"🔍 Начинаем AI-фильтрацию {len(news_list)} новостей...")
            
            filtered_news = []
            total_news = len(news_list)
            
            for i, news in enumerate(news_list, 1):
                try:
                    # Получаем заголовок и содержание новости
                    title = getattr(news, 'title', '') or getattr(news, 'raw_content', '')[:100]
                    content = getattr(news, 'content', '') or getattr(news, 'raw_content', '')
                    
                    if not title and not content:
                        logger.warning(f"⚠️ Новость {i}/{total_news}: пустой заголовок и содержание")
                        continue
                    
                    # Анализируем релевантность через AI
                    if self.ai_service:
                        try:
                            relevance_score = await self.ai_service.analyze_news_relevance(title, content)
                            
                            if relevance_score is not None and relevance_score >= 6:
                                filtered_news.append(news)
                                logger.info(f"✅ Новость {i}/{total_news}: релевантность {relevance_score}/10 - ВКЛЮЧЕНА")
                            else:
                                logger.info(f"❌ Новость {i}/{total_news}: релевантность {relevance_score}/10 - ИСКЛЮЧЕНА")
                                
                        except Exception as e:
                            logger.warning(f"⚠️ Ошибка AI анализа новости {i}/{total_news}: {e}")
                            # При ошибке AI включаем новость (fallback)
                            filtered_news.append(news)
                            logger.info(f"✅ Новость {i}/{total_news}: включена по fallback (ошибка AI)")
                    else:
                        # Если AI недоступен, используем fallback
                        logger.warning("⚠️ AI сервис недоступен, используем fallback фильтрацию")
                        filtered_news = news_list
                        break
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки новости {i}/{total_news}: {e}")
                    continue
            
            logger.info(f"🔍 AI-фильтрация завершена: {len(filtered_news)}/{total_news} новостей прошли фильтр")
            return filtered_news
            
        except Exception as e:
            logger.error(f"❌ Ошибка AI-фильтрации: {e}")
            # При ошибке возвращаем все новости
            logger.warning("⚠️ Возвращаем все новости из-за ошибки фильтрации")
            return news_list
    
    async def _create_news_summary(self, news: Any) -> str:
        """
        Создает краткое саммари для новости с помощью AI согласно ТЗ.
        
        Args:
            news: Объект новости
            
        Returns:
            str: Краткое саммари (50-100 слов)
        """
        try:
            # Используем AI сервис для генерации саммари согласно ТЗ
            if self.ai_service:
                try:
                    # Генерируем саммари с помощью AI
                    summary = await self.ai_service.generate_summary_only(
                        title=news.title,
                        content=news.content
                    )
                    
                    if summary and summary.strip():
                        logger.info(f"✅ AI саммари создано для новости: {news.title[:50]}...")
                        return summary.strip()
                    else:
                        logger.warning("⚠️ AI вернул пустое саммари, используем fallback")
                        
                except Exception as e:
                    logger.warning(f"⚠️ AI генерация не удалась, используем fallback: {e}")
            else:
                logger.warning("⚠️ AI сервис недоступен, используем fallback")
            
            # Fallback: создаем простое саммари
            return self._create_fallback_summary(news)
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания саммари: {e}")
            return self._create_fallback_summary(news)
    
    async def _save_summary_to_db(self, news_id: int, summary: str) -> None:
        """
        Сохраняет саммари в базу данных.
        
        Args:
            news_id: ID новости
            summary: Саммари для сохранения
        """
        try:
            if self.database_service:
                with self.database_service.get_session() as session:
                    from src.models.database import News
                    
                    # Находим новость и обновляем саммари
                    news = session.query(News).filter(News.id == news_id).first()
                    if news:
                        news.ai_summary = summary
                        session.commit()
                        logger.info(f"✅ Саммари сохранено в БД для новости {news_id}")
                    else:
                        logger.warning(f"⚠️ Новость {news_id} не найдена в БД")
                        
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения саммари в БД: {e}")
    
    def _create_fallback_summary(self, news: Any) -> str:
        """
        Создает простое саммари без AI.
        
        Args:
            news: Объект новости
            
        Returns:
            str: Простое саммари
        """
        try:
            # Берем первые 2-3 предложения из заголовка и контента
            content = f"{news.title}. {news.content}"
            sentences = content.split('.')[:3]
            
            # Очищаем и объединяем
            summary = '. '.join([s.strip() for s in sentences if s.strip()]) + '.'
            
            # Ограничиваем длину
            if len(summary) > 100:
                summary = summary[:97] + '...'
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Ошибка fallback саммари: {e}")
            return f"Новость: {news.title[:50]}..."
    
    def format_digest_for_telegram(self, digest: MorningDigest) -> str:
        """
        Форматирует дайджест для Telegram согласно ФТ.
        
        Args:
            digest: Объект дайджеста
            
        Returns:
            str: Отформатированный дайджест
        """
        try:
            if digest.news_count == 0:
                return "📭 Новостей для дайджеста не найдено."
            
            # Заголовок дайджеста
            formatted_digest = f"""
🌅 <b>УТРЕННИЙ ДАЙДЖЕСТ ИИ НОВОСТЕЙ</b>
📅 {digest.date.strftime('%d.%m.%Y %H:%M')}
📊 Всего новостей: {digest.news_count}

"""
            
            # Список новостей (по ФТ - только заголовок, саммари, источник)
            for i, news in enumerate(digest.news_items, 1):
                logger.info(f"🔍 Форматируем новость {i}: source_links='{news.source_links}'")
                formatted_digest += f"""
<b>{i}. {news.title}</b>
📝 {news.summary}
➡️ Источник: {news.source_links if news.source_links else 'Не указан'}

"""
            
            # Футер с вопросом кураторам (по ФТ)
            formatted_digest += """
<b>Вопрос кураторам:</b> Можно ли отправить эти новости экспертам?

🤖 <i>Создано автоматически системой PR-ассистента ZeBrains</i>
"""
            
            return formatted_digest.strip()
            
        except Exception as e:
            logger.error(f"❌ Ошибка форматирования дайджеста: {e}")
            return f"❌ Ошибка форматирования дайджеста: {str(e)}"
    
    async def send_digest_to_curators_chat(self, digest: MorningDigest, chat_id: str) -> bool:
        """
        Отправляет интерактивный дайджест в чат кураторов согласно ФТ.
        Разбивает длинные сообщения на части, если превышают лимит Telegram.
        
        Args:
            digest: Объект дайджеста
            chat_id: ID чата кураторов
            
        Returns:
            bool: Успешность отправки
        """
        try:
            logger.info(f"📤 Отправляем интерактивный дайджест в чат кураторов: {chat_id}")
            
            # Создаем интерактивный дайджест с inline кнопками
            message_text, buttons = self.create_interactive_digest_message(digest)
            
            # Проверяем длину сообщения (Telegram лимит: 4096 символов)
            max_length = config.message.max_digest_length - 100  # Оставляем запас для HTML тегов
            
            if len(message_text) <= max_length:
                # Сообщение короткое, отправляем как есть
                await self._send_single_message(chat_id, message_text, buttons)
                logger.info(f"✅ Интерактивный дайджест отправлен в чат кураторов (одно сообщение)")
            else:
                # Сообщение длинное, разбиваем на части по новостям
                await self._send_split_messages(chat_id, digest)
                logger.info(f"✅ Интерактивный дайджест отправлен в чат кураторов (разбит на части по новостям)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки интерактивного дайджеста в чат кураторов: {e}")
            return False

    async def _send_single_message(self, chat_id: str, message_text: str, buttons: list) -> bool:
        """
        Отправляет одно сообщение с inline кнопками.
        
        Args:
            chat_id: ID чата
            message_text: Текст сообщения
            buttons: Список кнопок
            
        Returns:
            bool: Успешность отправки
        """
        try:
            from telegram import InlineKeyboardMarkup
            reply_markup = InlineKeyboardMarkup(buttons)
            
            # Очищаем текст от неправильных HTML тегов, но сохраняем ссылки
            cleaned_text = self._clean_html_text(message_text)
            
            if self.bot:
                message = await self.bot.send_message(
                    chat_id=chat_id,
                    text=cleaned_text,
                    reply_markup=reply_markup
                )
                logger.info(f"✅ Сообщение отправлено через bot")
                
                # Сохраняем ID сообщения в сессии для одиночных сообщений
                if message and message.message_id:
                    self._save_digest_session(chat_id, [message.message_id], 0)
                    logger.info(f"💾 Сохранена сессия для одиночного сообщения: {message.message_id}")
            else:
                logger.error("❌ Bot недоступен, сообщение не отправлено")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки одиночного сообщения: {e}")
            return False

    async def _send_split_messages(self, chat_id: str, digest: MorningDigest) -> bool:
        """
        Разбивает дайджест на части по новостям и отправляет их с соответствующими кнопками.
        
        Args:
            chat_id: ID чата
            digest: Объект дайджеста
            
        Returns:
            bool: Успешность отправки
        """
        try:
            # Разбиваем дайджест на части по новостям
            parts = self._split_message_by_news(digest)
            
            if not parts:
                logger.error("❌ Не удалось разбить дайджест на части")
                return False
            
            logger.info(f"📤 Отправляем дайджест в {len(parts)} частях")
            
            # Список для хранения ID всех сообщений дайджеста
            message_ids = []
            
            # Отправляем каждую часть с соответствующими кнопками
            for i, part in enumerate(parts):
                # Создаем кнопки для текущей части
                part_buttons = []
                
                for news_idx in part['buttons']:
                    news = digest.news_items[news_idx]
                    if hasattr(news, 'id') and news.id is not None:
                        button_text = f"🗑️ Удалить {news_idx + 1}"
                        callback_data = f"remove_news_{news.id}"
                        from telegram import InlineKeyboardButton
                        part_buttons.append([
                            InlineKeyboardButton(button_text, callback_data=callback_data)
                        ])
                        logger.info(f"🔘 Создаю кнопку для части {i+1}: {button_text} -> {callback_data}")
                
                # Добавляем кнопку "Одобрить оставшиеся" только к последней части
                if i == len(parts) - 1:
                    from telegram import InlineKeyboardButton
                    approve_button = InlineKeyboardButton(
                        "✅ Одобрить оставшиеся", 
                        callback_data="approve_remaining"
                    )
                    part_buttons.append([approve_button])
                    logger.info(f"🔘 Добавляю кнопку одобрения к последней части")
                
                # Отправляем часть с кнопками
                if part_buttons:
                    if self.bot:
                        from telegram import InlineKeyboardMarkup
                        # Очищаем текст от неправильных HTML тегов, но сохраняем ссылки
                        cleaned_text = self._clean_html_text(part['text'])
                        message = await self.bot.send_message(
                            chat_id=chat_id,
                            text=cleaned_text,
                            reply_markup=InlineKeyboardMarkup(part_buttons)
                        )
                        message_ids.append(message.message_id)
                        logger.info(f"✅ Отправлена часть {i+1} из {len(parts)} с {len(part_buttons)} кнопками")
                    else:
                        await self._send_single_message(chat_id, part['text'], part_buttons)
                else:
                    # Отправляем без кнопок
                    if self.bot:
                        # Очищаем текст от неправильных HTML тегов, но сохраняем ссылки
                        cleaned_text = self._clean_html_text(part['text'])
                        message = await self.bot.send_message(
                            chat_id=chat_id,
                            text=cleaned_text
                        )
                        message_ids.append(message.message_id)
                        logger.info(f"✅ Отправлена часть {i+1} из {len(parts)} без кнопок")
                    else:
                        logger.error("❌ Bot недоступен, часть дайджеста не отправлена")
            
            # Сохраняем ID всех сообщений дайджеста в сессии
            if message_ids:
                self._save_digest_session(chat_id, message_ids, digest.news_count)
                logger.info(f"💾 Сохранены ID {len(message_ids)} сообщений дайджеста для чата {chat_id}")
            
            # НЕ деактивируем сессию здесь - она остается активной для модерации
            logger.info(f"✅ Дайджест отправлен, сессия активна для модерации")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки разбитых сообщений: {e}")
            return False

    def _clean_html_text(self, text: str) -> str:
        """
        Очищает текст от всех HTML тегов, кроме ссылок, и исправляет неправильные теги.
        
        Args:
            text: Исходный текст
            
        Returns:
            str: Очищенный текст с правильными HTML тегами
        """
        import re
        
        # Сначала исправляем неправильные теги типа <2>, <3>, <2,> и т.д.
        text = re.sub(r'<\d+[^>]*>', '', text)
        
        # Удаляем все HTML теги
        text = re.sub(r'<[^>]*>', '', text)
        
        # Удаляем оставшиеся символы < и > которые могли остаться
        text = re.sub(r'[<>]', '', text)
        
        # Добавляем переносы строк для читаемости
        # После точек, восклицательных и вопросительных знаков
        text = re.sub(r'([.!?])\s+', r'\1\n\n', text)
        
        # После двоеточий
        text = re.sub(r':\s+', ':\n', text)
        
        # После тире
        text = re.sub(r'—\s+', '—\n', text)
        
        # Удаляем множественные переносы строк
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Удаляем множественные пробелы
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Удаляем пробелы в начале и конце строк
        lines = text.split('\n')
        lines = [line.strip() for line in lines]
        text = '\n'.join(lines)
        
        # Удаляем пустые строки в начале и конце
        text = text.strip()
        
        return text

    def _split_message_by_news(self, digest: MorningDigest, max_length: int = None) -> list:
        """
        Разбивает дайджест на части по новостям, чтобы не разрывать новости посередине.
        
        Args:
            digest: Объект дайджеста
            max_length: Максимальная длина части
            
        Returns:
            list: Список частей с новостями и кнопками
        """
        if not digest.news_items:
            return []
        
        # Заголовок дайджеста
        header = f"""
🌅 УТРЕННИЙ ДАЙДЖЕСТ НОВОСТЕЙ
📅 Дата: {digest.date.strftime('%d.%m.%Y')}
📰 Всего новостей: {digest.news_count}

📋 НОВОСТИ ДЛЯ МОДЕРАЦИИ:
"""
        
        # Функция форматирования новости
        def format_news(i: int, news: DigestNews) -> str:
            return f"""
{i+1}. {news.summary}
➡️ Источник: {news.source_links if news.source_links else 'Не указан'}

"""
        
        # Используем универсальную утилиту для разбиения
        parts = MessageSplitter.split_by_items(
            items=digest.news_items,
            header=header,
            item_formatter=format_news,
            max_length=max_length,
            include_metadata=True
        )
        
        # Добавляем инструкции к последней части
        if parts:
            footer = """
💡 ИНСТРУКЦИИ:
• Нажмите кнопку "🗑️ Удалить" для каждой ненужной новости
• После удаления ненужных новостей нажмите "✅ Одобрить оставшиеся"
"""
            parts[-1]['text'] += footer
        
        return parts
    
    async def send_digest_to_curators_chat_auto(self, digest: MorningDigest) -> bool:
        """
        Автоматически отправляет дайджест в чат кураторов (по ФТ).
        
        Args:
            digest: Объект дайджеста
            
        Returns:
            bool: Успешность отправки
        """
        return await self.send_digest_to_curators_chat(digest, self.curators_chat_id)
    
    async def send_digest_to_specific_curator(self, digest: MorningDigest, curator_id: str) -> bool:
        """
        Отправляет дайджест конкретному куратору.
        
        Args:
            digest: Объект дайджеста
            curator_id: ID куратора
            
        Returns:
            bool: Успешность отправки
        """
        try:
            logger.info(f"📤 Отправляем дайджест куратору {curator_id}...")
            
            # Получаем куратора из БД
            with self.database_service.get_session() as session:
                from src.models.database import Curator
                curator = session.query(Curator).filter(Curator.id == curator_id).first()
            
            if not curator:
                logger.error(f"❌ Куратор {curator_id} не найден")
                return False
            
            # Создаем интерактивный дайджест с inline кнопками
            message_text, buttons = self.create_interactive_digest_message(digest)
            
            # Создаем InlineKeyboardMarkup
            from telegram import InlineKeyboardMarkup
            reply_markup = InlineKeyboardMarkup(buttons)
            
            # Отправляем через bot или notification service
            if self.bot:
                await self.bot.send_message(
                    chat_id=curator.telegram_id,
                    text=message_text,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
                logger.info(f"✅ Интерактивный дайджест отправлен куратору {curator.name} через bot")
            else:
                logger.error("❌ Bot недоступен, дайджест не отправлен куратору")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки дайджеста куратору {curator_id}: {e}")
            return False
    
    def _create_empty_digest(self) -> MorningDigest:
        """Создает пустой дайджест."""
        return MorningDigest(
            date=datetime.now(),
            news_count=0,
            news_items=[],
            curator_id=None
        )
    
    async def get_digest_statistics(self) -> Dict[str, Any]:
        """
        Получает статистику по дайджестам.
        
        Returns:
            Dict: Статистика дайджестов
        """
        try:
            # Получаем новости за разные периоды
            last_24h = await self._get_recent_news(hours=config.timeout.news_parsing_interval * 24)
            last_7d = await self._get_recent_news(hours=config.timeout.news_parsing_interval * 24 * 7)
            last_30d = await self._get_recent_news(hours=config.timeout.news_parsing_interval * 24 * 30)
            
            # Собираем статистику
            stats = {
                "last_24h": {
                    "count": len(last_24h)
                },
                "last_7d": {
                    "count": len(last_7d)
                },
                "last_30d": {
                    "count": len(last_30d)
                }
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {}

    def create_interactive_digest_message(self, digest: MorningDigest) -> tuple[str, list]:
        """
        Создает интерактивное сообщение с дайджестом и inline кнопками.
        
        Args:
            digest: Дайджест для отображения
            
        Returns:
            tuple: (текст сообщения, список inline кнопок)
        """
        if not digest.news_items:
            return "📭 Новостей для модерации не найдено", []
        
        # Заголовок дайджеста
        header = f"""
🌅 УТРЕННИЙ ДАЙДЖЕСТ НОВОСТЕЙ
📅 Дата: {digest.date.strftime('%d.%m.%Y')}
📰 Всего новостей: {digest.news_count}

📋 НОВОСТИ ДЛЯ МОДЕРАЦИИ:
"""
        
        # Список новостей
        news_list = ""
        for i, news in enumerate(digest.news_items, 1):
            logger.info(f"🔍 Форматируем новость {i}: source_links='{news.source_links}'")
            news_list += f"""
{i}. {news.summary}
➡️ Источник: {news.source_links if news.source_links else 'Не указан'}

"""
        
        # Инструкции
        footer = """
💡 ИНСТРУКЦИИ:
• Нажмите кнопку "🗑️ Удалить" для каждой ненужной новости
• После удаления ненужных новостей нажмите "✅ Одобрить оставшиеся"
"""
        
        message_text = header + news_list + footer
        
        # Создаем inline кнопки для каждой новости
        buttons = []
        logger.info(f"🔘 Начинаем создание кнопок для {len(digest.news_items)} новостей")
        
        for i, news in enumerate(digest.news_items):
            # Логируем информацию о новости для отладки
            logger.info(f"🔘 Обрабатываем новость {i+1}: ID={getattr(news, 'id', 'None')}, Title='{getattr(news, 'title', 'None')[:30]}...'")
            
            # Проверяем, что у новости есть ID
            if not hasattr(news, 'id') or news.id is None:
                logger.warning(f"⚠️ У новости {i+1} отсутствует ID, пропускаем кнопку")
                continue
                
            button_text = f"🗑️ Удалить {i+1}"
            callback_data = f"remove_news_{news.id}"
            logger.info(f"🔘 Создаю кнопку: {button_text} -> {callback_data}")
            buttons.append([
                InlineKeyboardButton(
                    button_text, 
                    callback_data=callback_data
                )
            ])
        
        # Кнопка для одобрения оставшихся новостей
        approve_button = InlineKeyboardButton(
            "✅ Одобрить оставшиеся", 
            callback_data="approve_remaining"
        )
        logger.info(f"🔘 Создаю кнопку одобрения: approve_remaining")
        buttons.append([approve_button])
        
        logger.info(f"🔘 Всего создано кнопок: {len(buttons)}")
        return message_text, buttons

    
    
    
    async def delete_digest_messages(self, chat_id: str) -> bool:
        """
        Удаляет все сообщения дайджеста для указанного чата.
        
        Args:
            chat_id: ID чата
            
        Returns:
            bool: Успешность удаления
        """
        try:
            logger.info(f"🗑️ Начинаем ПРОСТУЮ очистку всех сообщений дайджеста для чата: {chat_id}")
            
            if not self.bot:
                logger.warning(f"⚠️ Бот недоступен для чата {chat_id}")
                return False
            
            # ПРОСТОЕ решение: удаляем сообщения из текущей сессии
            total_deleted = await self._delete_all_digest_messages_in_chat(chat_id)
            
            # Очищаем сессию после удаления сообщений (теперь работает через БД)
            self.clear_digest_session(chat_id)
            logger.info(f"✅ Сессия дайджеста очищена для чата {chat_id}")
            
            logger.info(f"✅ ПРОСТАЯ очистка завершена, удалено {total_deleted} сообщений")
            return total_deleted > 0
            
        except Exception as e:
            logger.error(f"❌ Ошибка простой очистки: {e}")
            return False
    

    async def _delete_all_digest_messages_in_chat(self, chat_id: str) -> int:
        """
        Удаляет ВСЕ сообщения дайджеста в чате, используя ПРОСТОЙ подход.
        
        Args:
            chat_id: ID чата
            
        Returns:
            int: Количество удаленных сообщений
        """
        try:
            if not self.bot:
                logger.warning(f"⚠️ Бот недоступен для чата {chat_id}")
                return 0
            
            logger.info(f"🗑️ Начинаем ПРОСТУЮ очистку всех сообщений дайджеста в чате {chat_id}")
            
            # Получаем информацию о чате (best-effort)
            try:
                chat_info = await self.bot.get_chat(chat_id)
                logger.info(f"🔍 Получена информация о чате: {chat_info.title if hasattr(chat_info, 'title') else chat_id}")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось получить информацию о чате: {e}")
            
            deleted_count = 0
            
            # Сначала пытаемся удалить по ID из сессии
            session = self.get_digest_session(chat_id)
            if session and session.get('message_ids'):
                logger.info(f"🔍 Удаляем сообщения из текущей сессии: {session['message_ids']}")
                for msg_id in session['message_ids']:
                    try:
                        await self.bot.delete_message(
                            chat_id=int(chat_id), 
                            message_id=int(msg_id)
                        )
                        deleted_count += 1
                        logger.info(f"🗑️ Удалено сообщение сессии: {msg_id}")
                        await asyncio.sleep(0.1)
                    except Exception as e:
                        logger.warning(f"⚠️ Не удалось удалить сообщение сессии {msg_id}: {e}")
                        continue
            
            if deleted_count == 0:
                logger.warning(f"⚠️ Не удалось удалить ни одного сообщения дайджеста")
            
            logger.info(f"✅ ПРОСТАЯ очистка завершена, удалено {deleted_count} сообщений")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Ошибка простой очистки: {e}")
            return 0



# Пример использования
if __name__ == "__main__":
    print("🌅 Morning Digest Service - Тест")
    print("=" * 40)
    
    # Создаем mock сервисы для тестирования
    from unittest.mock import Mock
    
    mock_db = Mock()
    mock_ai = Mock()
    mock_bot = Mock()
    
    # Создаем сервис
    service = MorningDigestService(
        database_service=mock_db,
        ai_analysis_service=mock_ai,
        bot=mock_bot
    )
    
    print("✅ MorningDigestService создан успешно")
    print("📋 Функции:")
    print("   - create_morning_digest()")
    print("   - format_digest_for_telegram()")
    print("   - send_digest_to_curators()")
    print("   - send_digest_to_specific_curator()")
    print("   - get_digest_statistics()")
