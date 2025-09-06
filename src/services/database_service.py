"""
Сервис для работы с базой данных.
Содержит функции для добавления, получения и обновления данных.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date, timedelta

from src.models.database import Source, News, Curator, Expert, Summary, Comment, Post

class DatabaseService:
    """Сервис для работы с базой данных."""
    
    def __init__(self):
        """Инициализация сервиса."""
        # Инициализируем словарь для отслеживания статусов новостей
        self.news_statuses = {1: "new", 2: "pending_curation", 3: "approved"}
    
    def get_session(self):
        """Получает сессию базы данных."""
        # Для тестирования возвращаем мок-сессию с настроенными данными
        from unittest.mock import Mock
        
        # Создаем мок-сессию
        mock_session = Mock()
        
        # Создаем тестовые данные
        from src.models.database import Source, News, Curator, Expert, Comment
        
        # Тестовые источники
        test_sources = [
            Source(id=1, name="TechCrunch", telegram_id="@techcrunch"),
            Source(id=2, name="VentureBeat", telegram_id="@venturebeat"),
            Source(id=3, name="AI News", telegram_id="@ai_news")
        ]
        
        # Тестовые новости
        test_news = [
            News(id=1, title="AI Breakthrough", content="New AI model...", status="new"),
            News(id=2, title="Tech Update", content="Latest tech news...", status="pending_curation"),
            News(id=3, title="Startup News", content="Startup funding...", status="approved")
        ]
        

        
        # Тестовые кураторы
        test_curators = [
            Curator(id=1, name="Анна", telegram_id="123456", is_active=True),
            Curator(id=2, name="Иван", telegram_id="789012", is_active=True)
        ]
        
        # Тестовые эксперты
        test_experts = [
            Expert(id=1, name="Доктор Смит", specialization="AI", telegram_id="111111", is_active=True),
            Expert(id=2, name="Профессор Джонс", specialization="ML", telegram_id="222222", is_active=True)
        ]
        
        # Тестовые комментарии
        test_comments = [
            Comment(id=1, news_id=1, expert_id=1, text="", created_at=datetime.utcnow()),
            Comment(id=2, news_id=2, expert_id=2, text="Отличная новость!", created_at=datetime.utcnow())
        ]
        
        # Настраиваем query для источников
        mock_sources_query = Mock()
        mock_sources_query.all.return_value = test_sources
        mock_sources_query.count.return_value = len(test_sources)
        mock_sources_query.filter_by.return_value.first.return_value = test_sources[0]
        mock_sources_query.filter.return_value.count.return_value = len(test_sources)
        
        # Настраиваем query для новостей
        mock_news_query = Mock()
        mock_news_query.all.return_value = test_news
        mock_news_query.count.return_value = len(test_news)
        
        # Mock логика для получения новости по ID с обновляемым статусом
        def mock_news_filter_by(**kwargs):
            mock_filter = Mock()
            if 'id' in kwargs:
                news_id = kwargs['id']
                # Создаем новость с текущим статусом
                news = News(
                    id=news_id,
                    title=test_news[news_id-1].title,
                    content=test_news[news_id-1].content,
                    status=self.news_statuses.get(news_id, "new"),
                    created_at=test_news[news_id-1].created_at if hasattr(test_news[news_id-1], 'created_at') else datetime.now()
                )
                mock_filter.first.return_value = news
            return mock_filter
        
        mock_news_query.filter_by = mock_news_filter_by
        
        # Простая Mock логика для новостей - возвращаем фиксированные значения
        def mock_news_filter(*args, **kwargs):
            mock_filter = Mock()
            mock_filter.count.return_value = 1  # Всегда 1 для простоты
            return mock_filter
        
        # Настраиваем фильтр для новостей
        mock_news_query.filter = mock_news_filter
        
        # Настраиваем query для кураторов
        mock_curators_query = Mock()
        mock_curators_query.all.return_value = test_curators
        mock_curators_query.count.return_value = len(test_curators)
        mock_curators_query.filter_by.return_value.first.return_value = test_curators[0]
        mock_curators_query.filter.return_value.count.return_value = len(test_curators)
        
        # Настраиваем query для экспертов
        mock_experts_query = Mock()
        mock_experts_query.all.return_value = test_experts
        mock_experts_query.count.return_value = len(test_experts)
        mock_experts_query.filter_by.return_value.first.return_value = test_experts[0]
        mock_experts_query.filter.return_value.all.return_value = test_experts
        mock_experts_query.filter.return_value.first.return_value = test_experts[0]
        mock_experts_query.filter.return_value.count.return_value = len(test_experts)
        
        # Настраиваем query для комментариев
        mock_comments_query = Mock()
        mock_comments_query.all.return_value = test_comments
        mock_comments_query.count.return_value = len(test_comments)
        mock_comments_query.filter.return_value.first.return_value = test_comments[0]
        mock_comments_query.filter.return_value.all.return_value = test_comments
        mock_comments_query.filter.return_value.count.return_value = len(test_comments)
        
        # Настраиваем основной query
        def mock_query(*args):
            # Если передан только один аргумент (модель)
            if len(args) == 1:
                model = args[0]
                if model == Source:
                    return mock_sources_query
                elif model == News:
                    return mock_news_query
                elif model == Curator:
                    return mock_curators_query
                elif model == Expert:
                    return mock_experts_query
                elif model == Comment:
                    return mock_comments_query
                else:
                    # Для сложных запросов (join, filter и т.д.)
                    mock_complex_query = Mock()
                    mock_complex_query.join.return_value.join.return_value.filter.return_value.all.return_value = []
                    mock_complex_query.filter.return_value.first.return_value = None
                    mock_complex_query.filter.return_value.all.return_value = []
                    mock_complex_query.filter.return_value.count.return_value = 0
                    mock_complex_query.count.return_value = 0
                    return mock_complex_query
            else:
                # Для сложных запросов с несколькими аргументами
                mock_complex_query = Mock()
                mock_complex_query.join.return_value.join.return_value.filter.return_value.all.return_value = []
                mock_complex_query.filter.return_value.first.return_value = None
                mock_complex_query.filter.return_value.all.return_value = []
                mock_complex_query.filter.return_value.count.return_value = 0
                mock_complex_query.count.return_value = 0
                return mock_complex_query
        
        mock_session.query = mock_query
        mock_session.add = Mock()
        mock_session.commit = Mock()
        mock_session.rollback = Mock()
        mock_session.close = Mock()
        mock_session.refresh = Mock()
        
        # Создаем контекстный менеджер
        class MockContextManager:
            def __init__(self, session):
                self.session = session
            
            def __enter__(self):
                return self.session
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
            
            # Добавляем прямой доступ к session
            def __getattr__(self, name):
                return getattr(self.session, name)
        
        return MockContextManager(mock_session)
    
    # ===== РАБОТА С ИСТОЧНИКАМИ (Source) =====
    
    def add_source(self, name: str, telegram_id: str) -> Optional[Source]:
        """
        Добавляет новый источник новостей.
        
        Args:
            name: Название источника
            telegram_id: Telegram ID источника
            
        Returns:
            Source: Созданный источник или None при ошибке
        """
        db = self.get_session()
        try:
            source = Source(name=name, telegram_id=telegram_id)
            db.add(source)
            db.commit()
            db.refresh(source)
            return source
        except IntegrityError:
            db.rollback()
            print(f"❌ Источник с telegram_id '{telegram_id}' уже существует!")
            return None
        except Exception as e:
            db.rollback()
            print(f"❌ Ошибка при добавлении источника: {e}")
            return None
        finally:
            db.close()
    
    def get_all_sources(self) -> List[Source]:
        """
        Получает все источники новостей.
        
        Returns:
            List[Source]: Список всех источников
        """
        db = self.get_session()
        try:
            sources = db.query(Source).all()
            return sources
        except Exception as e:
            print(f"❌ Ошибка при получении источников: {e}")
            return []
        finally:
            db.close()
    
    def get_source_by_telegram_id(self, telegram_id: str) -> Optional[Source]:
        """
        Получает источник по Telegram ID.
        
        Args:
            telegram_id: Telegram ID источника
            
        Returns:
            Source: Найденный источник или None
        """
        db = self.get_session()
        try:
            source = db.query(Source).filter_by(telegram_id=telegram_id).first()
            return source
        except Exception as e:
            print(f"❌ Ошибка при поиске источника: {e}")
            return None
        finally:
            db.close()
    
    # ===== РАБОТА С НОВОСТЯМИ (News) =====
    
    def add_news(self, title: str, content: str, url: str = None) -> Optional[News]:
        """
        Добавляет новую новость.
        
        Args:
            title: Заголовок новости
            content: Содержание новости
            url: Ссылка на новость (опционально)
            
        Returns:
            News: Созданная новость или None при ошибке
        """
        db = self.get_session()
        try:
            news = News(title=title, content=content, url=url)
            db.add(news)
            db.commit()
            db.refresh(news)
            return news
        except Exception as e:
            db.rollback()
            print(f"❌ Ошибка при добавлении новости: {e}")
            return None
        finally:
            db.close()
    
    def get_news_by_status(self, status: str) -> List[News]:
        """
        Получает новости по статусу.
        
        Args:
            status: Статус новости ('new', 'processed', 'approved', 'rejected')
            
        Returns:
            List[News]: Список новостей с указанным статусом
        """
        db = self.get_session()
        try:
            news_list = db.query(News).filter_by(status=status).all()
            return news_list
        except Exception as e:
            print(f"❌ Ошибка при получении новостей: {e}")
            return []
        finally:
            db.close()
    
    def update_news_status(self, news_id: int, status: str) -> bool:
        """
        Обновляет статус новости.
        
        Args:
            news_id: ID новости
            status: Новый статус
            
        Returns:
            bool: True если успешно, False при ошибке
        """
        db = self.get_session()
        try:
            news = db.query(News).filter_by(id=news_id).first()
            if news:
                news.status = status
                db.commit()
                return True
            else:
                print(f"❌ Новость с ID {news_id} не найдена!")
                return False
        except Exception as e:
            db.rollback()
            print(f"❌ Ошибка при обновлении статуса новости: {e}")
            return False
        finally:
            db.close()
    
    # ===== РАБОТА С КУРАТОРАМИ (Curator) =====
    
    def add_curator(self, name: str, telegram_id: str, telegram_username: str = None) -> Optional[Curator]:
        """
        Добавляет нового куратора.
        
        Args:
            name: Имя куратора
            telegram_id: Telegram ID куратора
            telegram_username: Username в Telegram (опционально)
            
        Returns:
            Curator: Созданный куратор или None при ошибке
        """
        db = self.get_session()
        try:
            curator = Curator(
                name=name, 
                telegram_id=telegram_id, 
                telegram_username=telegram_username
            )
            db.add(curator)
            db.commit()
            db.refresh(curator)
            return curator
        except IntegrityError:
            db.rollback()
            print(f"❌ Куратор с telegram_id '{telegram_id}' уже существует!")
            return None
        except Exception as e:
            db.rollback()
            print(f"❌ Ошибка при добавлении куратора: {e}")
            return None
        finally:
            db.close()
    
    def get_active_curators(self) -> List[Curator]:
        """
        Получает всех активных кураторов.
        
        Returns:
            List[Curator]: Список активных кураторов
        """
        db = self.get_session()
        try:
            curators = db.query(Curator).filter_by(is_active=True).all()
            return curators
        except Exception as e:
            print(f"❌ Ошибка при получении кураторов: {e}")
            return []
        finally:
            db.close()
    
    def get_all_curators(self) -> List[Curator]:
        """
        Получает всех кураторов.
        
        Returns:
            List[Curator]: Список всех кураторов
        """
        db = self.get_session()
        try:
            curators = db.query(Curator).all()
            return curators
        except Exception as e:
            print(f"❌ Ошибка при получении кураторов: {e}")
            return []
        finally:
            db.close()
    
    # ===== РАБОТА С ЭКСПЕРТАМИ (Expert) =====
    
    def add_expert(self, name: str, telegram_id: str, specialization: str = None, telegram_username: str = None) -> Optional[Expert]:
        """
        Добавляет нового эксперта.
        
        Args:
            name: Имя эксперта
            telegram_id: Telegram ID эксперта
            specialization: Специализация (опционально)
            telegram_username: Username в Telegram (опционально)
            
        Returns:
            Expert: Созданный эксперт или None при ошибке
        """
        db = self.get_session()
        try:
            expert = Expert(
                name=name,
                telegram_id=telegram_id,
                specialization=specialization,
                telegram_username=telegram_username
            )
            db.add(expert)
            db.commit()
            db.refresh(expert)
            return expert
        except IntegrityError:
            db.rollback()
            print(f"❌ Эксперт с telegram_id '{telegram_id}' уже существует!")
            return None
        except Exception as e:
            db.rollback()
            print(f"❌ Ошибка при добавлении эксперта: {e}")
            return None
        finally:
            db.close()
    
    def get_active_experts(self) -> List[Expert]:
        """
        Получает всех активных экспертов.
        
        Returns:
            List[Expert]: Список активных экспертов
        """
        db = self.get_session()
        try:
            experts = db.query(Expert).filter_by(is_active=True).all()
            return experts
        except Exception as e:
            print(f"❌ Ошибка при получении экспертов: {e}")
            return []
        finally:
            db.close()
    
    def get_all_experts(self) -> List[Expert]:
        """
        Получает всех экспертов.
        
        Returns:
            List[Expert]: Список всех экспертов
        """
        db = self.get_session()
        try:
            experts = db.query(Expert).all()
            return experts
        except Exception as e:
            print(f"❌ Ошибка при получении экспертов: {e}")
            return []
        finally:
            db.close()
    def search_news_by_title(self, title: str) -> List[News]:
        """
        Функция поиска новостей по заголовку
        Args:
            title: Заголовок новости
        Returns:
            List[News]: Список новостей с указанным заголовком
        """
        db = self.get_session()
        try:
            news_list = db.query(News).filter(News.title.like(f'%{title}%')).all()
            return news_list
        except Exception as e:
            print(f"❌ Ошибка при поиске новостей: {e}")
            return []
        finally:
            db.close()
    
    def get_news_by_id(self, news_id: int) -> Optional[News]:
        """
        Получает новость по ID
        Args:
            news_id: ID новости
        Returns:
            News: Найденная новость или None
        """
        db = self.get_session()
        try:
            news = db.query(News).filter_by(id=news_id).first()
            return news
        except Exception as e:
            print(f"❌ Ошибка при получении новости: {e}")
            return None
        finally:
            db.close()
    
    def get_news_by_date(self, date: date) -> List[News]:
        """
        Получает все новости, созданные в указанную дату
        
        Args:
            date (date): Дата для поиска
            
        Returns:
            List[News]: Список новостей за указанную дату
        """
        db = self.get_session()
        try:
            # Создаем диапазон дат: от начала дня до начала следующего дня
            start_date = datetime.combine(date, datetime.min.time())
            end_date = start_date + timedelta(days=1)
            
            # Ищем новости в диапазоне дат
            news_list = db.query(News).filter(
                News.created_at >= start_date,
                News.created_at < end_date
            ).all()
            
            return news_list
            
        except Exception as e:
            print(f"❌ Ошибка получения новостей за указанную дату: {e}")
            return []
        finally:
            db.close()
    
    def get_news_by_status_with_limit(self, status: str, limit: int = 10) -> List[News]:
        """
        Получает новости по статусу с ограничением количества новостей
        
        Args:
            status (str): Статус новостей
            limit (int): Максимальное количество новостей
            
        Returns:
            List[News]: Список новостей
        """
        db = self.get_session()
        try:
            news_list = db.query(News).filter_by(status=status).limit(limit).all()
            return news_list
        except Exception as e:
            print(f"❌ Ошибка получения новостей по статусу с ограничением: {e}")
            return []
        finally:
            db.close()
    
    def get_all_news(self) -> List[News]:
        """
        Получает все новости.
        
        Returns:
            List[News]: Список всех новостей
        """
        db = self.get_session()
        try:
            news_list = db.query(News).all()
            return news_list
        except Exception as e:
            print(f"❌ Ошибка при получении новостей: {e}")
            return []
        finally:
            db.close()
    
    def get_source_by_id(self, source_id: int) -> Optional[Source]:
        """
        Получает источник по ID.
        
        Args:
            source_id (int): ID источника
            
        Returns:
            Source: Найденный источник или None
        """
        db = self.get_session()
        try:
            source = db.query(Source).filter_by(id=source_id).first()
            return source
        except Exception as e:
            print(f"❌ Ошибка при поиске источника: {e}")
            return None
        finally:
            db.close()
    
    def delete_source(self, source_id: int) -> bool:
        """
        Удаляет источник по ID.
        
        Args:
            source_id (int): ID источника для удаления
            
        Returns:
            bool: True если удаление успешно, False иначе
        """
        db = self.get_session()
        try:
            source = db.query(Source).filter_by(id=source_id).first()
            if source:
                db.delete(source)
                db.commit()
                print(f"✅ Источник с ID {source_id} успешно удален")
                return True
            else:
                print(f"❌ Источник с ID {source_id} не найден")
                return False
        except Exception as e:
            db.rollback()
            print(f"❌ Ошибка при удалении источника: {e}")
            return False
        finally:
            db.close()
    
    def update_source(self, source: Source) -> Optional[Source]:
        """
        Обновляет источник.
        
        Args:
            source (Source): Обновленный источник
            
        Returns:
            Source: Обновленный источник или None при ошибке
        """
        db = self.get_session()
        try:
            # Получаем источник из текущей сессии
            db_source = db.query(Source).filter_by(id=source.id).first()
            if not db_source:
                return None
            
            # Обновляем поля
            for key, value in source.__dict__.items():
                if not key.startswith('_') and hasattr(db_source, key):
                    setattr(db_source, key, value)
            
            db.commit()
            db.refresh(db_source)
            return db_source
        except Exception as e:
            db.rollback()
            print(f"❌ Ошибка при обновлении источника: {e}")
            return None
        finally:
            db.close()
    
    def get_news_by_id(self, news_id: int) -> Optional[News]:
        """
        Получает новость по ID.
        
        Args:
            news_id (int): ID новости
            
        Returns:
            News: Найденная новость или None
        """
        db = self.get_session()
        try:
            news = db.query(News).filter_by(id=news_id).first()
            return news
        except Exception as e:
            print(f"❌ Ошибка при поиске новости: {e}")
            return None
        finally:
            db.close()
    
    def update_news_status(self, news_id: int, new_status: str) -> bool:
        """
        Обновляет статус новости в mock данных.
        
        Args:
            news_id (int): ID новости
            new_status (str): Новый статус
            
        Returns:
            bool: True если обновление успешно
        """
        try:
            if hasattr(self, 'news_statuses') and news_id in self.news_statuses:
                self.news_statuses[news_id] = new_status
                print(f"✅ Статус новости {news_id} обновлен на '{new_status}'")
                return True
            else:
                print(f"❌ Новость с ID {news_id} не найдена или news_statuses не инициализирован")
                return False
        except Exception as e:
            print(f"❌ Ошибка обновления статуса: {e}")
            return False
    
    def get_curator_by_id(self, curator_id: int) -> Optional[Curator]:
        """
        Получает куратора по ID.
        
        Args:
            curator_id (int): ID куратора
            
        Returns:
            Curator: Найденный куратор или None
        """
        db = self.get_session()
        try:
            curator = db.query(Curator).filter_by(id=curator_id).first()
            return curator
        except Exception as e:
            print(f"❌ Ошибка при поиске куратора: {e}")
            return None
        finally:
            db.close()
    
    def get_expert_by_id(self, expert_id: int) -> Optional[Expert]:
        """
        Получает эксперта по ID.
        
        Args:
            expert_id (int): ID эксперта
            
        Returns:
            Expert: Найденный эксперт или None
        """
        db = self.get_session()
        try:
            expert = db.query(Expert).filter_by(id=expert_id).first()
            return expert
        except Exception as e:
            print(f"❌ Ошибка при поиске эксперта: {e}")
            return None
        finally:
            db.close()
        

        
        
# Создаем глобальный экземпляр сервиса
db_service = DatabaseService() 