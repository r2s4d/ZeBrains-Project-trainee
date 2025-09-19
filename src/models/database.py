# Импортируем необходимые модули из SQLAlchemy
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

# Создаем базовый класс для всех моделей
# Все наши модели будут наследоваться от этого класса
Base = declarative_base()

# Модель Source — источник новости (например, Telegram-канал)
class Source(Base):
    __tablename__ = 'sources'  # Имя таблицы в базе данных

    id = Column(Integer, primary_key=True)  # Уникальный идентификатор источника (автоматически увеличивается)
    name = Column(String, nullable=False)   # Название источника (например, "AI News Channel")
    telegram_id = Column(String, nullable=False, unique=True)  # Уникальный идентификатор Telegram-канала

    def __repr__(self):
        # Метод для красивого отображения объекта Source при печати
        return f"<Source(id={self.id}, name='{self.name}', telegram_id='{self.telegram_id}')>"

# Пояснения:
# - Base — это "родитель" для всех моделей, нужен для работы SQLAlchemy.
# - __tablename__ — имя таблицы в базе данных.
# - id — уникальный номер (primary key), нужен для идентификации каждой записи.
# - name — строка с названием источника.
# - telegram_id — строка с уникальным идентификатором Telegram-канала (например, @ai_news_channel).
# - __repr__ — служебный метод, чтобы удобно видеть объекты при отладке.

# Модель News — новость
class News(Base):
    __tablename__ = 'news'  # Имя таблицы в базе данных

    id = Column(Integer, primary_key=True)  # Уникальный идентификатор новости
    title = Column(String, nullable=False)  # Заголовок новости
    content = Column(Text, nullable=False)  # Полный текст новости (Text для длинных текстов)
    url = Column(String, nullable=True)     # Ссылка на оригинальную новость
    published_at = Column(DateTime, default=datetime.utcnow)  # Дата публикации новости
    created_at = Column(DateTime, default=datetime.utcnow)    # Дата добавления новости в нашу систему
    is_duplicate = Column(Boolean, default=False)  # Флаг, указывающий что это дубликат другой новости
    status = Column(String, default='new')  # Статус новости: 'new', 'pending', 'approved', 'rejected'
    curator_id = Column(String, nullable=True)  # Telegram ID куратора, который обработал новость
    curated_at = Column(DateTime, nullable=True)  # Дата обработки новости куратором
    channel_published_at = Column(DateTime, nullable=True)  # Дата публикации новости в нашем канале
    
    # Новые поля для реальных новостей из Telegram
    source_message_id = Column(BigInteger, nullable=True)  # ID сообщения в Telegram
    source_channel_username = Column(String, nullable=True)  # Username канала-источника
    source_url = Column(Text, nullable=True)  # URL на оригинальное сообщение
    raw_content = Column(Text, nullable=True)  # Исходный текст сообщения
    
    # Поля для AI анализа
    ai_summary = Column(Text, nullable=True)  # AI-генерированное саммари

    def __repr__(self):
        # Метод для красивого отображения объекта News при печати
        return f"<News(id={self.id}, title='{self.title[:50]}...', status='{self.status}')>"

# Пояснения к модели News:
# - title — заголовок новости (например, "OpenAI выпустил новую версию GPT-4")
# - content — полный текст новости (может быть длинным, поэтому используем Text)
# - url — ссылка на оригинальную новость (может быть пустой, поэтому nullable=True)
# - published_at — когда новость была опубликована в источнике
# - created_at — когда мы добавили новость в нашу систему
# - is_duplicate — флаг для дубликатов (если новость уже есть в системе)
# - status — статус обработки новости в нашей системе

# Модель NewsSource — связь между новостью и источником
# Эта таблица нужна потому что одна новость может быть в нескольких источниках
class NewsSource(Base):
    __tablename__ = 'news_sources'  # Имя таблицы в базе данных

    id = Column(Integer, primary_key=True)  # Уникальный идентификатор связи
    news_id = Column(Integer, ForeignKey('news.id'), nullable=False)  # Ссылка на новость
    source_id = Column(Integer, ForeignKey('sources.id'), nullable=False)  # Ссылка на источник
    source_url = Column(String, nullable=True)  # Конкретная ссылка на новость в этом источнике
    created_at = Column(DateTime, default=datetime.utcnow)  # Когда мы добавили эту связь

    def __repr__(self):
        # Метод для красивого отображения объекта NewsSource при печати
        return f"<NewsSource(id={self.id}, news_id={self.news_id}, source_id={self.source_id})>"

# Пояснения к модели NewsSource:
# - news_id — ссылка на таблицу news (ForeignKey означает "внешний ключ")
# - source_id — ссылка на таблицу sources
# - source_url — конкретная ссылка на новость в данном источнике
# - created_at — когда мы создали эту связь
# 
# Пример использования:
# Если новость "OpenAI выпустил GPT-5" есть в каналах @ai_news и @tech_news,
# то в таблице news_sources будет 2 записи:
# 1. news_id=1, source_id=1 (для @ai_news)
# 2. news_id=1, source_id=2 (для @tech_news)

# Модель Curator — куратор (человек, который фильтрует новости)
class Curator(Base):
    __tablename__ = 'curators'  # Имя таблицы в базе данных

    id = Column(Integer, primary_key=True)  # Уникальный идентификатор куратора
    name = Column(String, nullable=False)   # Имя куратора
    telegram_id = Column(String, nullable=False, unique=True)  # Telegram ID куратора
    telegram_username = Column(String, nullable=True)  # Username в Telegram (например, @john_doe)
    is_active = Column(Boolean, default=True)  # Активен ли куратор
    created_at = Column(DateTime, default=datetime.utcnow)  # Когда куратор был добавлен в систему

    def __repr__(self):
        # Метод для красивого отображения объекта Curator при печати
        return f"<Curator(id={self.id}, name='{self.name}', telegram_id='{self.telegram_id}')>"

# Модель Expert — эксперт (человек, который пишет комментарии к новостям)
class Expert(Base):
    __tablename__ = 'experts'  # Имя таблицы в базе данных

    id = Column(Integer, primary_key=True)  # Уникальный идентификатор эксперта
    name = Column(String, nullable=False)   # Имя эксперта
    telegram_id = Column(String, nullable=False, unique=True)  # Telegram ID эксперта
    telegram_username = Column(String, nullable=True)  # Username в Telegram
    specialization = Column(String, nullable=True)  # Специализация эксперта (например, "AI", "ML", "NLP")
    is_active = Column(Boolean, default=True)  # Активен ли эксперт
    created_at = Column(DateTime, default=datetime.utcnow)  # Когда эксперт был добавлен в систему

    # Связь с комментариями
    comments = relationship("Comment", back_populates="expert")

    def __repr__(self):
        # Метод для красивого отображения объекта Expert при печати
        return f"<Expert(id={self.id}, name='{self.name}', specialization='{self.specialization}')>"

# Пояснения к моделям Curator и Expert:
# - name — полное имя человека
# - telegram_id — уникальный идентификатор в Telegram (число)
# - telegram_username — username в Telegram (может быть пустым)
# - is_active — флаг активности (можно временно отключить человека)
# - created_at — когда человек был добавлен в систему
# - specialization — только для экспертов, указывает их специализацию

# Модель Summary — краткое саммари новости (генерируется ИИ)
class Summary(Base):
    __tablename__ = 'summaries'  # Имя таблицы в базе данных

    id = Column(Integer, primary_key=True)  # Уникальный идентификатор саммари
    news_id = Column(Integer, ForeignKey('news.id'), nullable=False)  # Ссылка на новость
    text = Column(Text, nullable=False)  # Текст саммари (краткое содержание новости)
    created_at = Column(DateTime, default=datetime.utcnow)  # Когда саммари было создано
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Когда саммари было обновлено

    def __repr__(self):
        # Метод для красивого отображения объекта Summary при печати
        return f"<Summary(id={self.id}, news_id={self.news_id}, text='{self.text[:50]}...')>"

# Модель Comment — комментарий эксперта к новости
class Comment(Base):
    __tablename__ = 'comments'  # Имя таблицы в базе данных

    id = Column(Integer, primary_key=True)  # Уникальный идентификатор комментария
    news_id = Column(Integer, ForeignKey('news.id'), nullable=False)  # Ссылка на новость
    expert_id = Column(Integer, ForeignKey('experts.id'), nullable=False)  # Ссылка на эксперта
    text = Column(Text, nullable=False)  # Текст комментария/аналитики
    created_at = Column(DateTime, default=datetime.utcnow)  # Когда комментарий был создан
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Когда комментарий был обновлен

    # Связь с экспертом
    expert = relationship("Expert", back_populates="comments")

    def __repr__(self):
        # Метод для красивого отображения объекта Comment при печати
        return f"<Comment(id={self.id}, news_id={self.news_id}, expert_id={self.expert_id}, text='{self.text[:50]}...')>"

# Пояснения к моделям Summary и Comment:
# - news_id — ссылка на новость, к которой относится саммари/комментарий
# - text — текст саммари или комментария (может быть длинным)
# - created_at — когда запись была создана
# - updated_at — когда запись была обновлена (автоматически обновляется при изменении)
# - expert_id — только для комментариев, указывает на эксперта, который написал комментарий
# 
# Пример использования:
# 1. ИИ создает саммари для новости "OpenAI выпустил GPT-5" → запись в таблице summaries
# 2. Эксперт Иван пишет комментарий к этой новости → запись в таблице comments
# 3. Позже эти два текста объединяются в финальный пост

# Модель Post — итоговый пост для публикации в Telegram-канале
class Post(Base):
    __tablename__ = 'posts'  # Имя таблицы в базе данных

    id = Column(Integer, primary_key=True)  # Уникальный идентификатор поста
    news_id = Column(Integer, ForeignKey('news.id'), nullable=False)  # Ссылка на новость
    summary_id = Column(Integer, ForeignKey('summaries.id'), nullable=False)  # Ссылка на саммари
    comment_id = Column(Integer, ForeignKey('comments.id'), nullable=True)  # Ссылка на комментарий эксперта (может быть пустым)
    title = Column(String, nullable=False)  # Заголовок поста для публикации
    content = Column(Text, nullable=False)  # Полный текст поста (объединенный саммари + комментарий)
    image_url = Column(String, nullable=True)  # Ссылка на изображение к посту
    status = Column(String, default='draft')  # Статус поста: 'draft', 'pending_approval', 'approved', 'published', 'rejected'
    curator_id = Column(Integer, ForeignKey('curators.id'), nullable=True)  # Куратор, который одобрил пост
    published_at = Column(DateTime, nullable=True)  # Когда пост был опубликован в канале
    created_at = Column(DateTime, default=datetime.utcnow)  # Когда пост был создан в системе
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Когда пост был обновлен

    def __repr__(self):
        # Метод для красивого отображения объекта Post при печати
        return f"<Post(id={self.id}, title='{self.title[:50]}...', status='{self.status}')>"

# Пояснения к модели Post:
# - news_id — ссылка на исходную новость
# - summary_id — ссылка на саммари (обязательно)
# - comment_id — ссылка на комментарий эксперта (может быть пустым, если эксперт не написал комментарий)
# - title — заголовок поста для публикации (может отличаться от заголовка новости)
# - content — полный текст поста (объединенный саммари + комментарий + исправления)
# - image_url — ссылка на изображение, которое будет прикреплено к посту
# - status — статус поста в процессе публикации
# - curator_id — куратор, который одобрил пост (может быть пустым, если пост еще не одобрен)
# - published_at — когда пост был опубликован в Telegram-канале
# - created_at — когда пост был создан в системе
# - updated_at — когда пост был обновлен (например, после правок куратора)
# 
# Статусы поста:
# - 'draft' — черновик (только что создан)
# - 'pending_approval' — ожидает одобрения куратора
# - 'approved' — одобрен куратором
# - 'published' — опубликован в канале
# - 'rejected' — отклонен куратором

# Модель DigestSession — сессия дайджеста для отслеживания сообщений
class DigestSession(Base):
    __tablename__ = 'digest_sessions'  # Имя таблицы в базе данных

    id = Column(Integer, primary_key=True)  # Уникальный идентификатор сессии
    chat_id = Column(String, nullable=False)  # ID чата в Telegram
    message_ids = Column(Text, nullable=False)  # JSON строка с ID сообщений дайджеста
    news_count = Column(Integer, nullable=False)  # Количество новостей в дайджесте
    created_at = Column(DateTime, default=datetime.utcnow)  # Когда сессия была создана
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Когда сессия была обновлена
    is_active = Column(Boolean, default=True)  # Активна ли сессия

    def __repr__(self):
        # Метод для красивого отображения объекта DigestSession при печати
        return f"<DigestSession(id={self.id}, chat_id='{self.chat_id}', news_count={self.news_count}, is_active={self.is_active})>"

# Пояснения к модели DigestSession:
# - chat_id — ID чата в Telegram (например, "-1001234567890")
# - message_ids — JSON строка с массивом ID сообщений (например, "[237, 238, 239, 240]")
# - news_count — количество новостей в дайджесте
# - created_at — когда сессия была создана
# - updated_at — когда сессия была обновлена (автоматически обновляется)
# - is_active — флаг активности сессии (можно деактивировать старые сессии)
# 
# Пример использования:
# 1. Создается дайджест с 21 новостью → запись в digest_sessions
# 2. При удалении новости сессия обновляется → updated_at обновляется
# 3. После завершения модерации сессия деактивируется → is_active = False

# Модель BotSession — состояния бота для устойчивости к перезапускам
class BotSession(Base):
    __tablename__ = 'bot_sessions'  # Имя таблицы в базе данных

    id = Column(Integer, primary_key=True)  # Уникальный идентификатор сессии
    session_type = Column(String(50), nullable=False)  # Тип сессии: 'digest_edit', 'photo_wait', 'expert_session', 'curator_moderation', 'current_digest'
    user_id = Column(String(50), nullable=True)  # ID пользователя/эксперта (может быть пустым для системных сессий)
    chat_id = Column(String(50), nullable=True)  # ID чата (может быть пустым для пользовательских сессий)
    data = Column(Text, nullable=False)  # JSON строка с данными сессии
    status = Column(String(50), default='active')  # Статус сессии: 'active', 'completed', 'expired', 'cancelled'
    expires_at = Column(DateTime, nullable=True)  # Время истечения сессии (для автоочистки)
    created_at = Column(DateTime, default=datetime.utcnow)  # Когда сессия была создана
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Когда сессия была обновлена

    def __repr__(self):
        # Метод для красивого отображения объекта BotSession при печати
        return f"<BotSession(id={self.id}, type='{self.session_type}', user_id='{self.user_id}', status='{self.status}')>"

# Пояснения к модели BotSession:
# - session_type — тип сессии, определяет что именно хранится в data
#   * 'digest_edit' — ожидание правок дайджеста от куратора
#   * 'photo_wait' — ожидание фото для публикации от куратора
#   * 'expert_session' — активная сессия работы эксперта
#   * 'curator_moderation' — процесс модерации куратором
#   * 'current_digest' — текущий дайджест для публикации
#   * 'interactive_moderation' — интерактивная модерация
# - user_id — ID пользователя (куратора, эксперта) для которого создана сессия
# - chat_id — ID чата для системных сессий (например, дайджест для конкретного чата)
# - data — JSON строка с данными сессии (структура зависит от session_type)
# - status — статус сессии для отслеживания состояния
# - expires_at — время истечения для автоматической очистки старых сессий
# - created_at — когда сессия была создана
# - updated_at — когда сессия была обновлена (автоматически обновляется)
# 
# Примеры использования:
# 1. Куратор получает дайджест → session_type='curator_moderation', data={'approved_news': [], 'rejected_news': []}
# 2. Эксперт начинает работу → session_type='expert_session', data={'news_items': [...], 'current_index': 0}
# 3. Ожидание фото → session_type='photo_wait', data={'digest_text': '...', 'channel_id': '...'}
# 4. Текущий дайджест → session_type='current_digest', data={'digest_text': '...', 'formatted': True}

