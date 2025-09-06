# -*- coding: utf-8 -*-
"""
PostFormatterService - сервис для форматирования постов

Этот сервис создает красивые посты для Telegram канала в стиле "цифрового сотрудника":
- Форматирование заголовков с эмодзи
- Структурированные новости с нумерацией
- Цитаты экспертов в стиле Telegram
- Источники с эмодзи
- Призывы к действию
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from src.models.database import News, Summary, Comment, Expert


class PostFormatterService:
    """
    Сервис для форматирования постов в стиле "цифрового сотрудника".
    
    Основные функции:
    - Создание заголовков с эмодзи
    - Форматирование новостей с нумерацией
    - Обработка цитат экспертов
    - Добавление источников
    - Создание призывов к действию
    """
    
    def __init__(self):
        """Инициализация сервиса."""
        self.digital_employee_name = "Алекс"
        self.digital_employee_role = "цифровой SMM-менеджер ZeBrains"
        
    def format_post_title(self, title: str) -> str:
        """
        Форматирует заголовок поста с эмодзи.
        
        Args:
            title: Исходный заголовок
            
        Returns:
            Отформатированный заголовок
        """
        # Добавляем эмодзи в зависимости от содержания
        emoji = self._get_title_emoji(title)
        return f"{emoji} {title}"
    
    def _get_title_emoji(self, title: str) -> str:
        """
        Выбирает подходящий эмодзи для заголовка.
        
        Args:
            title: Заголовок новости
            
        Returns:
            Эмодзи
        """
        title_lower = title.lower()
        
        # Проверяем точные совпадения слов
        words = title_lower.split()
        
        if any(word in ['прорыв', 'революция', 'первый'] for word in words):
            return "🚀"
        elif any(word in ['ai', 'ии', 'нейросеть', 'gpt', 'openai'] for word in words):
            return "🤖"
        elif any(word in ['google', 'microsoft', 'meta', 'apple'] for word in words):
            return "💼"
        elif any(word in ['стартап', 'инвестиции', 'финансирование'] for word in words):
            return "💰"
        elif any(word in ['исследование', 'наука', 'университет'] for word in words):
            return "🔬"
        elif any(word in ['новый'] for word in words):
            return "🚀"
        else:
            return "📰"
    
    def format_introduction(self, expert_name: Optional[str] = None) -> str:
        """
        Создает введение от "цифрового сотрудника".
        
        Args:
            expert_name: Имя эксперта недели
            
        Returns:
            Текст введения
        """
        if expert_name:
            # Используем правильный падеж для русского языка
            expert_name_correct = self._get_expert_name_in_correct_case(expert_name)
            # Определяем правильный предлог
            preposition = self._get_correct_preposition(expert_name)
            return f"Привет! Я {self.digital_employee_name}, {self.digital_employee_role}. Эту неделю разбираем горячие новости ИИ {preposition} {expert_name_correct}! Честно скажу - последние достижения в области ИИ заставили даже моих нейронов поволноваться!"
        else:
            return f"Привет! Я {self.digital_employee_name}, {self.digital_employee_role}. Эту неделю разбираем горячие новости ИИ! Честно скажу - последние достижения в области ИИ заставили даже моих нейронов поволноваться!"
    
    def format_news_item(self, news: News, summary: Summary, comment: Optional[Comment] = None, index: int = 1) -> str:
        """
        Форматирует одну новость с саммари и комментарием эксперта.
        
        Args:
            news: Объект новости
            summary: Саммари новости
            comment: Комментарий эксперта (опционально)
            index: Номер новости
            
        Returns:
            Отформатированная новость
        """
        # Основная новость
        news_text = f"{index}. {news.title}\n{summary.text}\n"
        
        # Добавляем комментарий эксперта, если есть
        if comment and comment.expert:
            expert_quote = self._format_expert_quote(comment)
            news_text += f"\n{expert_quote}\n"
        
        return news_text
    
    def _format_expert_quote(self, comment: Comment) -> str:
        """
        Форматирует цитату эксперта в стиле Telegram.
        
        Args:
            comment: Комментарий эксперта
            
        Returns:
            Отформатированная цитата
        """
        expert = comment.expert
        expert_title = self._get_expert_title(expert.specialization)
        
        # Используем формат цитаты Telegram с символом >
        return f'> {comment.text}\n> - {expert.name}, {expert_title}'
    
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
            'Engineering': 'технический директор'
        }
        
        return titles.get(specialization, 'эксперт по ИИ')
    
    def _get_expert_name_in_correct_case(self, name: str) -> str:
        """
        Возвращает имя эксперта в правильном падеже для русского языка.
        
        Args:
            name: Имя эксперта
            
        Returns:
            Имя в правильном падеже (творительный падеж)
        """
        # Разделяем имя и фамилию
        parts = name.split()
        if len(parts) < 2:
            return name
        
        first_name = parts[0]
        last_name = parts[1]
        
        # Склоняем имя (творительный падеж)
        if first_name.endswith('н'):
            first_name = first_name + 'ом'
        elif first_name.endswith('й'):
            first_name = first_name[:-1] + 'ем'
        elif first_name.endswith('а'):
            first_name = first_name[:-1] + 'ой'
        elif first_name.endswith('я'):
            first_name = first_name[:-1] + 'ей'
        else:
            first_name = first_name + 'ом'
        
        # Склоняем фамилию (творительный падеж)
        if last_name.endswith('ов'):
            last_name = last_name[:-2] + 'овым'
        elif last_name.endswith('ев'):
            last_name = last_name[:-2] + 'евым'
        elif last_name.endswith('ин'):
            last_name = last_name[:-2] + 'иным'
        elif last_name.endswith('ова'):
            last_name = last_name[:-3] + 'овой'
        elif last_name.endswith('ева'):
            last_name = last_name[:-3] + 'евой'
        elif last_name.endswith('ина'):
            last_name = last_name[:-3] + 'иной'
        elif last_name.endswith('ский'):
            last_name = last_name[:-4] + 'ским'
        elif last_name.endswith('цкий'):
            last_name = last_name[:-4] + 'цким'
        elif last_name.endswith('ская'):
            last_name = last_name[:-4] + 'ой'
        elif last_name.endswith('цкая'):
            last_name = last_name[:-4] + 'ой'
        elif last_name.endswith('ой'):
            last_name = last_name[:-2] + 'ым'
        elif last_name.endswith('ий'):
            last_name = last_name[:-2] + 'им'
        elif last_name.endswith('ая'):
            last_name = last_name[:-2] + 'ой'
        
        return f"{first_name} {last_name}"
    
    def _get_correct_preposition(self, name: str) -> str:
        """
        Возвращает правильный предлог для имени в творительном падеже.
        
        Args:
            name: Имя эксперта
            
        Returns:
            Правильный предлог
        """
        # Разделяем имя и фамилию
        parts = name.split()
        if len(parts) < 2:
            return "вместе с"
        
        first_name = parts[0]
        
        # Определяем предлог в зависимости от первой буквы имени
        if first_name.lower().startswith(('а', 'е', 'ё', 'и', 'о', 'у', 'ы', 'э', 'ю', 'я')):
            return "вместе с"
        else:
            return "вместе со"
    
    def format_sources(self, sources: List[str]) -> str:
        """
        Форматирует список источников.
        
        Args:
            sources: Список источников
            
        Returns:
            Отформатированные источники
        """
        if not sources:
            return ""
        
        if len(sources) == 1:
            sources_text = "Источник"
        else:
            sources_text = "Источники"
        
        sources_text += ": " + ", ".join([f"@{source}" for source in sources])
        
        return f"➡️ {sources_text}"
    
    def format_conclusion(self) -> str:
        """
        Создает заключение с призывом к действию.
        
        Returns:
            Текст заключения
        """
        return """На этом у меня всё! Какая новость удивила больше всего?
Делитесь в комментариях!

Подписывайтесь на наш канал, чтобы не пропустить следующий дайджест - впереди ещё больше интересного мира ИИ!"""
    
    def create_full_post(self, news_items: List[Dict[str, Any]], title: str = None) -> str:
        """
        Создает полный пост со всеми элементами.
        
        Args:
            news_items: Список новостей с саммари и комментариями
            title: Заголовок поста (опционально)
            
        Returns:
            Полный отформатированный пост
        """
        if not news_items:
            return "📝 Нет новостей для публикации"
        
        # Заголовок
        if title:
            post_title = self.format_post_title(title)
        else:
            post_title = self.format_post_title("Нейросети меняют мир: главные новости недели")
        
        # Введение
        expert_name = None
        if news_items and 'comment' in news_items[0] and news_items[0]['comment']:
            expert_name = news_items[0]['comment'].expert.name
        
        introduction = self.format_introduction(expert_name)
        
        # Новости
        news_section = ""
        for i, item in enumerate(news_items, 1):
            news_text = self.format_news_item(
                news=item['news'],
                summary=item['summary'],
                comment=item.get('comment'),
                index=i
            )
            news_section += news_text + "\n"
            
            # Добавляем источники
            if 'sources' in item and item['sources']:
                sources_text = self.format_sources(item['sources'])
                news_section += f"{sources_text}\n"
            
            news_section += "\n"
        
        # Заключение
        conclusion = self.format_conclusion()
        
        # Собираем полный пост
        full_post = f"{post_title}\n\n{introduction}\n\n{news_section}{conclusion}"
        
        return full_post
    
    def create_single_news_post(self, news: News, summary: Summary, comment: Optional[Comment] = None, sources: List[str] = None) -> str:
        """
        Создает пост для одной новости.
        
        Args:
            news: Новость
            summary: Саммари
            comment: Комментарий эксперта (опционально)
            sources: Список источников (опционально)
            
        Returns:
            Отформатированный пост
        """
        # Заголовок
        post_title = self.format_post_title(news.title)
        
        # Введение
        expert_name = comment.expert.name if comment and comment.expert else None
        introduction = self.format_introduction(expert_name)
        
        # Новость
        news_text = self.format_news_item(news, summary, comment, 1)
        
        # Источники
        sources_text = ""
        if sources:
            sources_text = self.format_sources(sources) + "\n\n"
        
        # Заключение
        conclusion = self.format_conclusion()
        
        # Собираем пост
        full_post = f"{post_title}\n\n{introduction}\n\n{news_text}{sources_text}{conclusion}"
        
        return full_post
    
    def create_daily_digest(self, news_items: List[Dict[str, Any]]) -> str:
        """
        Создает ежедневный дайджест.
        
        Args:
            news_items: Список новостей
            
        Returns:
            Отформатированный дайджест
        """
        if not news_items:
            return "📝 Нет новостей для дайджеста"
        
        # Заголовок
        today = datetime.now().strftime("%d.%m.%Y")
        post_title = self.format_post_title(f"Дайджест ИИ-новостей за {today}")
        
        # Введение
        introduction = f"Привет! Я {self.digital_employee_name}, {self.digital_employee_role}. Вот что произошло в мире ИИ за сегодня!"
        
        # Новости
        news_section = ""
        for i, item in enumerate(news_items, 1):
            news_text = self.format_news_item(
                news=item['news'],
                summary=item['summary'],
                comment=item.get('comment'),
                index=i
            )
            news_section += news_text + "\n"
            
            # Добавляем источники
            if 'sources' in item and item['sources']:
                sources_text = self.format_sources(item['sources'])
                news_section += f"{sources_text}\n"
            
            news_section += "\n"
        
        # Заключение
        conclusion = f"На этом всё на сегодня! Всего новостей: {len(news_items)}\n\nПодписывайтесь на наш канал, чтобы не пропустить завтрашний дайджест! 🚀"
        
        # Собираем дайджест
        full_digest = f"{post_title}\n\n{introduction}\n\n{news_section}{conclusion}"
        
        return full_digest
    
    def format_daily_digest(self, news_list: List[News]) -> str:
        """
        Форматирует ежедневный дайджест новостей.
        
        Args:
            news_list: Список новостей для дайджеста
            
        Returns:
            str: Отформатированный дайджест
        """
        if not news_list:
            return "📰 Нет новостей для дайджеста"
        
        # Заголовок дайджеста
        digest = f"""
🔥 **Ежедневный дайджест AI News**

👋 Привет! Я {self.digital_employee_name}, {self.digital_employee_role}, и сегодня у меня для вас {len(news_list)} важных новостей из мира искусственного интеллекта.

"""
        
        # Добавляем новости
        for i, news in enumerate(news_list, 1):
            digest += f"""
{i}. **{news.title}**

{news.content[:200]}...

"""
        
        # Заключение
        digest += f"""
💡 **Что думают эксперты:**
Пока эксперты анализируют новости, но скоро у нас будут их комментарии!

➡️ **Источники:** @ai_news, @tech_crunch, @venture_beat

🚀 **Подписывайтесь на наш канал** и будьте в курсе всех событий в мире ИИ!

#AI #MachineLearning #TechNews #ZeBrains
        """
        
        return digest.strip()
    
    def format_weekly_digest(self, news_list: List[News]) -> str:
        """
        Форматирует еженедельный дайджест новостей.
        
        Args:
            news_list: Список новостей для дайджеста
            
        Returns:
            str: Отформатированный еженедельный дайджест
        """
        if not news_list:
            return "📰 Нет новостей для еженедельного дайджеста"
        
        # Заголовок дайджеста
        digest = f"""
🔥 **Еженедельный дайджест AI News**

👋 Привет! Я {self.digital_employee_name}, {self.digital_employee_role}, и сегодня у меня для вас {len(news_list)} важных новостей из мира искусственного интеллекта за неделю.

"""
        
        # Добавляем новости
        for i, news in enumerate(news_list, 1):
            digest += f"""
{i}. **{news.title}**

{news.content[:200]}...

"""
        
        # Заключение
        digest += f"""
💡 **Что думают эксперты:**
Пока эксперты анализируют новости, но скоро у нас будут их комментарии!

➡️ **Источники:** @ai_news, @tech_crunch, @venture_beat

🚀 **Подписывайтесь на наш канал** и будьте в курсе всех событий в мире ИИ!

#AI #MachineLearning #TechNews #ZeBrains
        """
        
        return digest.strip()
    
    def format_single_news(self, news: News) -> str:
        """
        Форматирует отдельную новость для публикации.
        
        Args:
            news: Новость для форматирования
            
        Returns:
            str: Отформатированная новость
        """
        # Определяем эмодзи для заголовка
        title_emojis = {
            "openai": "🤖",
            "gpt": "🧠", 
            "google": "🔍",
            "microsoft": "💻",
            "ai": "🤖",
            "ml": "📊",
            "startup": "🚀",
            "investment": "💰",
            "research": "🔬",
            "course": "📚"
        }
        
        # Выбираем эмодзи на основе заголовка
        title_lower = news.title.lower()
        emoji = "📰"  # По умолчанию
        
        for keyword, emoji_icon in title_emojis.items():
            if keyword in title_lower:
                emoji = emoji_icon
                break
        
        # Форматируем новость
        formatted_news = f"""
{emoji} **{news.title}**

{news.content[:300]}...

"""
        
        # Добавляем метаданные
        if hasattr(news, 'importance_score') and news.importance_score:
            formatted_news += f"⭐ **Важность:** {news.importance_score}/10\n\n"
        
        # Добавляем источник
        if hasattr(news, 'source_id') and news.source_id:
            formatted_news += f"📡 **Источник:** ID {news.source_id}\n\n"
        
        # Добавляем время создания
        if hasattr(news, 'created_at') and news.created_at:
            formatted_news += f"📅 **Дата:** {news.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        
        # Добавляем хештеги
        formatted_news += """
#AI #MachineLearning #TechNews #ZeBrains

🚀 **Подписывайтесь на наш канал** для получения самых свежих новостей об ИИ!
        """
        
        return formatted_news.strip() 