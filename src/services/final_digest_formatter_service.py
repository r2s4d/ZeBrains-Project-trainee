# -*- coding: utf-8 -*-
"""
FinalDigestFormatterService - сервис для создания финального дайджеста по ТЗ

Этот сервис создает персонализированный дайджест от имени "цифрового сотрудника"
с интеграцией комментариев экспертов согласно функциональным требованиям.

Основные функции:
- AI-персонализация введения и заключения
- Естественная интеграция комментариев экспертов
- Форматирование по стандартам Telegram
- Создание привлекательных заголовков с эмодзи
- Следование ТЗ по структуре и стилю
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from src.models.database import News, Comment, Expert
from src.config import config
from src.services.ai_analysis_service import AIAnalysisService
from src.utils.message_splitter import MessageSplitter

# Настройка логирования
logger = logging.getLogger(__name__)

class FinalDigestFormatterService:
    """
    Сервис для создания финального дайджеста по ТЗ.
    
    Создает персонализированный дайджест от имени "цифрового сотрудника"
    с интеграцией комментариев экспертов и AI-персонализацией.
    """
    
    def __init__(self, ai_service: AIAnalysisService):
        """
        Инициализация сервиса.
        
        Args:
            ai_service: Сервис для работы с AI
        """
        self.ai_service = ai_service
        self.digital_employee_name = "Алекс"
        self.digital_employee_role = "цифровой SMM-менеджер ZeBrains"
        
        logger.info("FinalDigestFormatterService инициализирован")
    
    async def create_final_digest(
        self,
        approved_news: List,
        expert_comments: Dict[int, Dict],
        expert_of_week,
        news_sources: Dict[int, List[str]] = None
    ) -> str:
        """
        Создает финальный дайджест по ТЗ.
        
        Args:
            approved_news: Список одобренных новостей
            expert_comments: Словарь комментариев экспертов (news_id -> comment)
            expert_of_week: Эксперт недели
            
        Returns:
            Отформатированный дайджест
        """
        try:
            logger.info(f"🎨 Создание финального дайджеста для {len(approved_news)} новостей")
            
            # 1. Создаем заголовок
            title = self._create_title(approved_news)
            
            # 2. Создаем персонализированное введение
            introduction = await self._generate_introduction(expert_of_week, len(approved_news))
            
            # 3. Сохраняем источники для использования в форматировании
            self._current_sources = news_sources or {}
            logger.info(f"🔍 Отладка источников в FinalDigestFormatterService: {self._current_sources}")
            
            # 4. Форматируем новости с комментариями
            news_section = await self._format_news_section(approved_news, expert_comments)
            
            # 5. Создаем персонализированное заключение
            conclusion = await self._generate_conclusion(len(approved_news))
            
            # 6. Собираем полный дайджест
            full_digest = f"{title}\n\n{introduction}\n\n{news_section}\n{conclusion}"
            
            logger.info("✅ Финальный дайджест создан успешно")
            return full_digest
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания финального дайджеста: {e}")
            return "❌ Ошибка создания дайджеста"
    
    def _create_title(self, news_items: List[News]) -> str:
        """
        Создает заголовок дайджеста по ТЗ.
        
        Требования по ТЗ:
        - Формат: жирный шрифт
        - Перед заголовком ставится эмодзи
        - Длина: до 10 слов
        - Ёмкий и привлекательный
        
        Args:
            news_items: Список новостей
            
        Returns:
            Отформатированный заголовок
        """
        # Определяем эмодзи на основе тем новостей
        emoji = self._get_title_emoji(news_items)
        
        # Создаем заголовок
        title = "ИИ меняет мир: главные новости недели"
        
        # Форматируем по ТЗ (жирный шрифт в Telegram)
        return f"<b>{emoji} {title}</b>"
    
    def _get_title_emoji(self, news_items: List[News]) -> str:
        """
        Выбирает эмодзи для заголовка по ТЗ.
        
        Требования по ТЗ:
        - 🔥, 🚀 или 📰 перед заголовком
        - Не более 1 эмодзи на блок
        
        Args:
            news_items: Список новостей
            
        Returns:
            Эмодзи
        """
        # Анализируем темы новостей
        ai_keywords = ['ai', 'ии', 'нейросеть', 'gpt', 'openai', 'машинное обучение']
        breakthrough_keywords = ['прорыв', 'революция', 'первый', 'новый']
        
        all_titles = " ".join([news.title.lower() for news in news_items])
        
        if any(keyword in all_titles for keyword in breakthrough_keywords):
            return "🚀"  # Прорывные новости
        elif any(keyword in all_titles for keyword in ai_keywords):
            return "🤖"  # AI новости
        else:
            return "📰"  # Общие новости
    
    async def _generate_introduction(self, expert: Expert, news_count: int) -> str:
        """
        Создает персонализированное введение с помощью AI.
        
        Требования по ТЗ:
        - Обычный текст (без выделения)
        - Длина: 1-2 предложения (до 30 слов)
        - От имени "цифрового сотрудника" в неформальном стиле
        - Представление эксперта недели
        - Профессиональный, но разговорный язык
        - Легкие шутки и интересные замечания уместны
        
        Args:
            expert: Эксперт недели
            news_count: Количество новостей
            
        Returns:
            Персонализированное введение
        """
        try:
            expert_title = self._get_expert_title(expert.specialization if hasattr(expert, 'specialization') else 'AI')
            
            prompt = f"""
            Создай введение для дайджеста новостей ИИ от цифрового SMM-менеджера Алекса.
            
            Эксперт недели: {expert.name if hasattr(expert, 'name') else 'Эксперт'}, {expert_title}
            Количество новостей: {news_count}
            
            Требования:
            - Обычный текст (без выделения жирным или курсивом)
            - Длина: 1-2 предложения (до 30 слов)
            - От имени "цифрового сотрудника" в неформальном стиле
            - Представление эксперта недели
            - Профессиональный, но разговорный язык
            - Легкие шутки и интересные замечания уместны
            - Персонализированный подход к подаче новостей
            - ОБЯЗАТЕЛЬНО упомяни компанию ZeBrains
            
            Пример стиля: "Привет! Я Алекс, цифровой SMM-менеджер ZeBrains. На этой неделе разбираем новости ИИ вместе со Степаном Игониным, руководителем отдела ИИ."
            
            Создай уникальное введение в этом стиле.
            """
            
            introduction = await self.ai_service.analyze_text(prompt)
            logger.info("✅ Персонализированное введение создано с помощью AI")
            return introduction
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания введения: {e}")
            # Fallback введение
            expert_title = self._get_expert_title(expert.get('specialization', 'AI'))
            return f"Привет! Я {self.digital_employee_name}, {self.digital_employee_role}. На этой неделе разбираем новости ИИ вместе с {expert.get('name', 'Эксперт')}, {expert_title}."
    
    async def _format_news_section(self, news_items: List[Dict], expert_comments: Dict[int, Dict]) -> str:
        """
        Форматирует секцию новостей с комментариями экспертов.
        
        Требования по ТЗ:
        - Каждая новость нумеруется (1., 2., 3.)
        - Обычный текст
        - Длина: 1-3 предложения (50-100 слов)
        - Цитата эксперта интегрируется в текст саммари
        - Выделяется кавычками
        - После кавычек в скобках указывается имя эксперта и должность
        - Источники с эмодзи ➡️
        - Пустая строка между новостями
        
        Args:
            news_items: Список новостей
            expert_comments: Комментарии экспертов
            
        Returns:
            Отформатированная секция новостей
        """
        news_section = ""
        
        for i, news in enumerate(news_items, 1):
            # Получаем комментарий эксперта
            news_id = news.get('id') if isinstance(news, dict) else news.id
            comment = expert_comments.get(news_id)
            
            # Логируем для диагностики
            logger.info(f"🔍 Новость {i}: ID={news_id}, комментарий={comment is not None}")
            if comment:
                logger.info(f"📝 Комментарий: {comment.get('text', '')[:100]}...")
            
            # Форматируем новость
            news_text = await self._format_single_news(news, comment, i)
            news_section += news_text + "\n\n"
        
        return news_section.strip()
    
    async def _format_single_news(self, news: Dict, comment: Optional[Dict], index: int) -> str:
        """
        Форматирует одну новость с комментарием эксперта.
        
        Args:
            news: Новость
            comment: Комментарий эксперта (опционально)
            index: Номер новости
            
        Returns:
            Отформатированная новость
        """
        # Используем готовое саммари из БД (ai_summary)
        if hasattr(news, 'ai_summary') and news.ai_summary:
            # Используем готовое саммари из БД
            summary = news.ai_summary
            logger.info(f"✅ Используем готовое саммари из БД для новости: {news.title[:50]}...")
        elif hasattr(news, 'summary') and news.summary:
            # Fallback: используем старое саммари
            summary = news.summary
            logger.info(f"⚠️ Используем fallback саммари для новости: {news.title[:50]}...")
        else:
            # Последний fallback: создаем саммари с помощью AI
            summary = await self._create_ai_summary(news)
            logger.warning(f"⚠️ Создаем новое саммари с помощью AI для новости: {news.title[:50]}...")
        
        # Очищаем заголовок и саммари от звездочек
        clean_summary = self._clean_markdown_artifacts(summary)
        
        news_text = f"{index}. {clean_summary}"
        
        # Интегрируем комментарий эксперта, если есть
        if comment:
            integrated_text = self._integrate_expert_comment(news_text, comment)
            news_text = integrated_text
        
        # Добавляем источники (если переданы)
        if hasattr(self, '_current_sources') and self._current_sources:
            news_id = news.get('id') if isinstance(news, dict) else news.id
            sources_for_news = self._current_sources.get(news_id)
            logger.info(f"🔍 Источники для новости {news_id}: {sources_for_news}")
            sources_text = self._format_sources(news, sources_for_news)
            if sources_text:
                news_text += f"\n\n{sources_text}"
                logger.info(f"✅ Добавлены источники к новости {news_id}: {sources_text}")
            else:
                logger.warning(f"⚠️ Не удалось отформатировать источники для новости {news_id}")
        
        return news_text
    
    async def _create_ai_summary(self, news: Dict, existing_summary: str = None) -> str:
        """
        Создает качественное саммари новости с помощью AI (максимум 100 слов).
        
        Args:
            news: Новость
            existing_summary: Существующее саммари (опционально)
            
        Returns:
            Качественное саммари
        """
        try:
            content = news.content if hasattr(news, 'content') else str(news)
            
            if existing_summary:
                prompt = f"""
                Создай краткое саммари новости для дайджеста (максимум 100 слов).
                
                Заголовок: {news.title}
                Существующее саммари: {existing_summary}
                Полный контент: {content}
                
                Требования:
                - Максимум 100 слов
                - Сохрани основную суть новости
                - Используй простой и понятный язык
                - Сделай текст интересным для читателя
                - Органично умести информацию в лимит слов
                
                Верни только саммари без дополнительных комментариев.
                """
            else:
                prompt = f"""
                Создай краткое саммари новости для дайджеста (максимум 100 слов).
                
                Заголовок: {news.title}
                Контент: {content}
                
                Требования:
                - Максимум 100 слов
                - Сохрани основную суть новости
                - Используй простой и понятный язык
                - Сделай текст интересным для читателя
                - Органично умести информацию в лимит слов
                
                Верни только саммари без дополнительных комментариев.
                """
            
            summary = await self.ai_service.analyze_text(prompt)
            
            # Проверяем, что саммари не превышает 100 слов
            words = summary.split()
            if len(words) > 100:
                summary = ' '.join(words[:100]) + "..."
            
            logger.info(f"✅ AI саммари создано: {len(words)} слов")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания AI саммари: {e}")
            # Fallback - используем оригинальный контент
            content = news.content if hasattr(news, 'content') else str(news)
            words = content.split()
            if len(words) > 100:
                return ' '.join(words[:100]) + "..."
            return content
    
    def _integrate_expert_comment(self, news_text: str, comment: Dict) -> str:
        """
        Интегрирует комментарий эксперта в текст новости в стиле Telegram.
        
        Требования по ТЗ:
        - Комментарий эксперта в отдельном блоке
        - Зеленый блок с кавычками (как в Telegram)
        - После кавычек в скобках указывается имя эксперта и должность
        - Естественный переход в тексте
        
        Args:
            news_text: Текст новости
            comment: Комментарий эксперта
            
        Returns:
            Текст с интегрированным комментарием
        """
        try:
            expert_title = self._get_expert_title(comment.get('expert', {}).get('specialization', 'AI'))
            expert_name = comment.get('expert', {}).get('name', 'Эксперт')
            
            # Создаем комментарий в стиле Telegram
            comment_text = comment.get('text', '')
            
            # Форматируем комментарий как в Telegram (зеленый блок с кавычками)
            formatted_comment = f"""
<blockquote>"{comment_text}"

— {expert_name}, {expert_title}</blockquote>
"""
            
            # Добавляем комментарий к новости
            news_with_comment = f"{news_text}\n\n{formatted_comment}"
            
            logger.info(f"✅ Комментарий эксперта добавлен в стиле Telegram")
            return news_with_comment
            
        except Exception as e:
            logger.error(f"❌ Ошибка интеграции комментария: {e}")
            # Fallback интеграция
            expert_title = self._get_expert_title(comment.get('expert', {}).get('specialization', 'AI'))
            expert_name = comment.get('expert', {}).get('name', 'Эксперт')
            return f"{news_text}\n\n<blockquote>\"{comment.get('text', '')}\"\n\n— {expert_name}, {expert_title}</blockquote>"
    
    def _format_sources(self, news: Dict, sources: List[str] = None) -> str:
        """
        Форматирует источники новости по ТЗ.
        
        Требования по ТЗ:
        - Формат: текст с гиперссылкой на Telegram-пост из источника
        - Перед ссылкой ставится эмодзи ➡️
        - Если источников несколько, они перечисляются через запятую (до 3 источников)
        
        Args:
            news: Новость
            
        Returns:
            Отформатированные источники
        """
        if sources:
            # Источники могут приходить в HTML формате из get_news_sources
            formatted_sources = []
            for source in sources[:3]:  # Максимум 3 источника
                if source.startswith('<a href=') and '</a>' in source:
                    # Если это HTML ссылка, используем как есть (оставляем в HTML формате)
                    formatted_sources.append(source)
                elif source.startswith('[') and '](' in source:
                    # Если это уже готовая Markdown ссылка, конвертируем в HTML для совместимости
                    import re
                    match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', source)
                    if match:
                        text, url = match.groups()
                        formatted_sources.append(f'<a href="{url}">{text}</a>')
                    else:
                        formatted_sources.append(source)
                elif source.startswith('http'):
                    # Если это URL, создаем HTML ссылку напрямую
                    formatted_sources.append(f'<a href="{source}">Источник</a>')
                else:
                    # Если это просто текст, используем как есть
                    formatted_sources.append(source)
            
            sources_text = ", ".join(formatted_sources)
            return f"➡️ {sources_text}"
        
        return ""
    
    def _clean_markdown_artifacts(self, text: str) -> str:
        """
        Очищает текст от звездочек и других markdown артефактов.
        
        Args:
            text: Исходный текст
            
        Returns:
            Очищенный текст с HTML тегами
        """
        try:
            # Убираем двойные звездочки ** и заменяем на HTML теги
            import re
            
            # Заменяем **текст** на <b>текст</b>
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            
            # Убираем одинарные звездочки *
            text = re.sub(r'\*([^*]+)\*', r'<i>\1</i>', text)
            
            # Убираем оставшиеся звездочки
            text = text.replace('*', '')
            
            # Убираем лишние пробелы
            text = re.sub(r'\s+', ' ', text).strip()
            
            logger.debug(f"🧹 Текст очищен от markdown артефактов")
            return text
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки текста: {e}")
            return text
    
    async def _generate_conclusion(self, news_count: int) -> str:
        """
        Создает персонализированное заключение с помощью AI.
        
        Требования по ТЗ:
        - Обычный текст
        - Длина: 1 предложение (до 15 слов)
        - Неформальное завершение от имени цифрового сотрудника
        - Призыв к действию с эмодзи (🚀, 📢)
        - Профессиональный, но разговорный язык
        
        Args:
            news_count: Количество новостей
            
        Returns:
            Персонализированное заключение
        """
        try:
            prompt = f"""
            Создай заключение для дайджеста новостей ИИ от цифрового SMM-менеджера Алекса.
            
            Количество новостей: {news_count}
            
            Требования:
            - Обычный текст
            - Длина: 1 предложение (до 15 слов)
            - Неформальное завершение от имени цифрового сотрудника
            - Призыв к действию с эмодзи (🚀, 📢)
            - Профессиональный, но разговорный язык
            - Персонализированный подход
            
            Пример по ТЗ: "На этом у меня всё! Какая новость вас удивила больше всего? Делитесь в комментариях! 🔥"
            
            Создай уникальное заключение в этом стиле.
            """
            
            conclusion = await self.ai_service.analyze_text(prompt)
            logger.info("✅ Персонализированное заключение создано с помощью AI")
            return conclusion
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания заключения: {e}")
            # Fallback заключение
            return f"На этом у меня всё! Какая новость вас удивила больше всего? Делитесь в комментариях! 🔥"
    
    def _get_expert_title(self, specialization: str) -> str:
        """
        Возвращает должность эксперта на основе специализации.
        
        Args:
            specialization: Специализация эксперта
            
        Returns:
            Должность
        """
        titles = {
            'AI': 'руководитель отдела ИИ',
            'ML': 'руководитель отдела машинного обучения',
            'NLP': 'руководитель отдела обработки естественного языка',
            'CV': 'руководитель отдела компьютерного зрения',
            'Data Science': 'руководитель отдела Data Science',
            'Research': 'научный руководитель',
            'Engineering': 'технический директор',
            'CEO': 'CEO и сооснователь ZeBrains',
            'CTO': 'технический директор',
            'Тестирование': 'тестовый эксперт'
        }
        
        return titles.get(specialization, 'эксперт по ИИ')
    
    def check_grammar_and_punctuation(self, text: str) -> str:
        """
        Проверяет и исправляет грамматику и пунктуацию с помощью AI.
        
        Args:
            text: Текст для проверки
            
        Returns:
            Исправленный текст
        """
        try:
            prompt = f"""
            Проверь и исправь грамматику и пунктуацию в следующем тексте.
            Сохрани смысл и стиль, но исправь ошибки.
            
            Текст: {text}
            
            Требования:
            - Исправь грамматические ошибки
            - Исправь пунктуацию
            - Сохрани стиль и тон
            - Сохрани смысл
            - Верни только исправленный текст
            """
            
            corrected_text = self.ai_service.analyze_text(prompt)
            
            # Если AI вернул fallback-текст, возвращаем исходный текст
            if corrected_text in ["Текст обработан успешно.", "Интересная новость в сфере искусственного интеллекта."]:
                logger.info("⚠️ AI вернул fallback-текст, используем исходный текст")
                return text
            
            logger.info("✅ Грамматика и пунктуация проверены с помощью AI")
            return corrected_text
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки грамматики: {e}")
            return text  # Возвращаем исходный текст при ошибке
    
    def split_digest_message(self, digest: str, max_length: int = None) -> List[str]:
        """
        Разделяет длинный дайджест на части для отправки в Telegram.
        
        Принцип как в MorningDigestService - сохранение структуры при разделении.
        
        Args:
            digest: Полный дайджест
            max_length: Максимальная длина сообщения
            
        Returns:
            Список частей дайджеста
        """
        # Используем универсальную утилиту для разбиения по блокам
        return MessageSplitter.split_by_blocks(
            text=digest,
            max_length=max_length,
            block_separator='\n\n',
            sentence_separator='. '
        )
