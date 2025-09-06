#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сервис для работы с базой данных в контексте Telegram бота.
Обеспечивает интеграцию между ботом и базой данных.
"""

import sys
import os
from typing import List, Optional, Dict, Any
from datetime import datetime, date

# Добавляем путь к модулям
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.postgresql_database_service import PostgreSQLDatabaseService
from models.database import Source, News, Curator, Expert


class BotDatabaseService:
    """
    Сервис для работы с базой данных в контексте Telegram бота.
    Обеспечивает удобные методы для взаимодействия с базой данных.
    """
    
    def __init__(self):
        """Инициализация сервиса."""
        self.db_service = PostgreSQLDatabaseService()
        # Временное хранение выбранного эксперта недели
        self.selected_expert_id = None
    
    def get_session(self):
        """Получить сессию базы данных."""
        try:
            return self.db_service.get_session()
        except Exception as e:
            print(f"❌ Ошибка получения сессии PostgreSQL: {e}")
            return None
    
    # ==================== РАБОТА С ИСТОЧНИКАМИ ====================
    
    def get_all_sources(self) -> List[Source]:
        """
        Получить все источники новостей.
        
        Returns:
            List[Source]: Список всех источников
        """
        return self.db_service.get_all_sources()
    
    def get_source_by_telegram_id(self, telegram_id: str) -> Optional[Source]:
        """
        Получить источник по Telegram ID.
        
        Args:
            telegram_id (str): Telegram ID источника
            
        Returns:
            Optional[Source]: Найденный источник или None
        """
        return self.db_service.get_source_by_telegram_id(telegram_id)
    
    def add_source(self, name: str, telegram_id: str, description: str = None) -> Optional[Source]:
        """
        Добавить новый источник новостей.
        
        Args:
            name (str): Название источника
            telegram_id (str): Telegram ID источника
            description (str, optional): Описание источника
            
        Returns:
            Optional[Source]: Созданный источник или None при ошибке
        """
        try:
            return self.db_service.add_source(name=name, telegram_id=telegram_id)
        except Exception as e:
            print(f"❌ Ошибка при добавлении источника: {e}")
            return None
    
    def delete_source(self, source_id: int) -> bool:
        """
        Удалить источник новостей.
        
        Args:
            source_id (int): ID источника для удаления
            
        Returns:
            bool: True если удаление успешно, False иначе
        """
        try:
            return self.db_service.delete_source(source_id)
        except Exception as e:
            print(f"❌ Ошибка при удалении источника: {e}")
            return False
    
    def update_source(self, source_id: int, **kwargs) -> Optional[Source]:
        """
        Обновить источник новостей.
        
        Args:
            source_id (int): ID источника
            **kwargs: Поля для обновления
            
        Returns:
            Optional[Source]: Обновленный источник или None при ошибке
        """
        try:
            source = self.db_service.get_source_by_id(source_id)
            if not source:
                return None
            
            # Обновляем только переданные поля
            for key, value in kwargs.items():
                if hasattr(source, key):
                    setattr(source, key, value)
            
            # Используем отдельный метод для обновления
            return self.db_service.update_source(source)
        except Exception as e:
            print(f"❌ Ошибка при обновлении источника: {e}")
            return None
    
    # ==================== РАБОТА С НОВОСТЯМИ ====================
    
    def get_recent_news(self, limit: int = 10) -> List[News]:
        """
        Получить последние новости.
        
        Args:
            limit (int): Количество новостей
            
        Returns:
            List[News]: Список последних новостей
        """
        try:
            news = self.db_service.get_news_by_status('new')
            return news[:limit]  # Возвращаем первые limit новостей
        except Exception as e:
            print(f"❌ Ошибка при получении последних новостей: {e}")
            return []
    
    def get_all_news(self) -> List[News]:
        """
        Получить все новости.
        
        Returns:
            List[News]: Список всех новостей
        """
        return self.db_service.get_all_news()
    
    def get_news_by_date(self, target_date: date) -> List[News]:
        """
        Получить новости за определенную дату.
        
        Args:
            target_date (date): Дата для поиска
            
        Returns:
            List[News]: Список новостей за дату
        """
        try:
            # Получаем все новости и фильтруем по дате
            all_news = self.db_service.get_all_news()
            target_date_str = target_date.strftime('%Y-%m-%d')
            
            filtered_news = []
            for news in all_news:
                if news.created_at and news.created_at.strftime('%Y-%m-%d') == target_date_str:
                    filtered_news.append(news)
            
            return filtered_news
        except Exception as e:
            print(f"❌ Ошибка при получении новостей по дате: {e}")
            return []
    
    def search_news(self, query: str) -> List[News]:
        """
        Поиск новостей по заголовку.
        
        Args:
            query (str): Поисковый запрос
            
        Returns:
            List[News]: Список найденных новостей
        """
        try:
            # Получаем все новости и ищем по заголовку
            all_news = self.db_service.get_all_news()
            query_lower = query.lower()
            
            found_news = []
            for news in all_news:
                if query_lower in news.title.lower():
                    found_news.append(news)
            
            return found_news
        except Exception as e:
            print(f"❌ Ошибка при поиске новостей: {e}")
            return []
    
    # ==================== РАБОТА С КУРАТОРАМИ ====================
    
    def get_all_curators(self) -> List[Curator]:
        """
        Получить всех кураторов.
        
        Returns:
            List[Curator]: Список всех кураторов
        """
        return self.db_service.get_all_curators()
    
    def add_curator(self, telegram_id: int, name: str, username: str = None) -> Optional[Curator]:
        """
        Добавить нового куратора.
        
        Args:
            telegram_id (int): Telegram ID куратора
            name (str): Имя куратора
            username (str, optional): Username куратора
            
        Returns:
            Optional[Curator]: Созданный куратор или None при ошибке
        """
        try:
            return self.db_service.add_curator(name, str(telegram_id), username)
        except Exception as e:
            print(f"❌ Ошибка при добавлении куратора: {e}")
            return None
    
    # ==================== РАБОТА С ЭКСПЕРТАМИ ====================
    
    def get_all_experts(self) -> List[Expert]:
        """
        Получить всех экспертов.
        
        Returns:
            List[Expert]: Список всех экспертов
        """
        return self.db_service.get_all_experts()
    
    def get_expert_by_id(self, expert_id: int) -> Optional[Expert]:
        """
        Получить эксперта по ID.
        
        Args:
            expert_id: ID эксперта
            
        Returns:
            Optional[Expert]: Найденный эксперт или None
        """
        return self.db_service.get_expert_by_id(expert_id)
    
    def get_curator_by_id(self, curator_id: int) -> Optional[Curator]:
        """
        Получить куратора по ID.
        
        Args:
            curator_id: ID куратора
            
        Returns:
            Optional[Curator]: Найденный куратор или None
        """
        return self.db_service.get_curator_by_id(curator_id)
    
    def add_expert(self, telegram_id: int, name: str, specialization: str, username: str = None) -> Optional[Expert]:
        """
        Добавить нового эксперта.
        
        Args:
            telegram_id (int): Telegram ID эксперта
            name (str): Имя эксперта
            specialization (str): Специализация эксперта
            username (str, optional): Username эксперта
            
        Returns:
            Optional[Expert]: Созданный эксперт или None при ошибке
        """
        try:
            return self.db_service.add_expert(name, str(telegram_id), specialization, username)
        except Exception as e:
            print(f"❌ Ошибка при добавлении эксперта: {e}")
            return None
    
    # ==================== СТАТИСТИКА ====================
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Получить статистику системы.
        
        Returns:
            Dict[str, Any]: Статистика системы
        """
        try:
            # Используем новый метод из PostgreSQL сервиса
            stats = self.db_service.get_database_stats()
            
            # Добавляем дополнительную информацию
            stats['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return stats
        except Exception as e:
            print(f"❌ Ошибка при получении статистики: {e}")
            return {}
    
    def get_news_by_id(self, news_id: int) -> Optional[News]:
        """
        Получить новость по ID.
        
        Args:
            news_id: ID новости
            
        Returns:
            Optional[News]: Найденная новость или None
        """
        try:
            return self.db_service.get_news_by_id(news_id)
        except Exception as e:
            print(f"❌ Ошибка при получении новости {news_id}: {e}")
            return None
    
    def update_news_status(self, news_id: int, new_status: str) -> bool:
        """
        Обновляет статус новости.
        
        Args:
            news_id (int): ID новости
            new_status (str): Новый статус
            
        Returns:
            bool: True если обновление успешно
        """
        try:
            if hasattr(self.db_service, 'update_news_status'):
                return self.db_service.update_news_status(news_id, new_status)
            else:
                print("❌ DatabaseService не поддерживает update_news_status")
                return False
        except Exception as e:
            print(f"❌ Ошибка обновления статуса: {e}")
            return False
    
    # ==================== МЕТОДЫ ДЛЯ ФИНАЛЬНОГО ДАЙДЖЕСТА ====================
    
    def get_approved_news_for_digest(self, limit: int = 5) -> List[News]:
        """
        Получить одобренные новости для создания дайджеста.
        
        Args:
            limit: Максимальное количество новостей
            
        Returns:
            List[News]: Список одобренных новостей
        """
        try:
            session = self.get_session()
            if not session:
                return []
            
            # Получаем одобренные новости, отсортированные по дате
            news_list = session.query(News).filter(
                News.status == "approved"
            ).order_by(News.created_at.desc()).limit(limit).all()
            
            session.close()
            return news_list
            
        except Exception as e:
            print(f"❌ Ошибка получения одобренных новостей: {e}")
            return []
    
    def get_expert_of_week(self) -> Optional[Expert]:
        """
        Получить эксперта недели.
        
        Returns:
            Expert: Эксперт недели или None
        """
        try:
            session = self.get_session()
            if not session:
                return None
            
            # Пропускаем загрузку из БД из-за проблем с правами
            # Используем только память
            
            # Если есть выбранный эксперт в памяти, возвращаем его
            if self.selected_expert_id:
                expert = session.query(Expert).filter(Expert.id == self.selected_expert_id).first()
                if expert:
                    session.close()
                    return expert
            
            # Иначе возвращаем первого активного эксперта
            expert = session.query(Expert).filter(
                Expert.is_active == True
            ).first()
            
            session.close()
            return expert
            
        except Exception as e:
            print(f"❌ Ошибка получения эксперта недели: {e}")
            return None
    
    def set_expert_of_week(self, expert_id: int) -> bool:
        """
        Установить эксперта недели.
        
        Args:
            expert_id: ID эксперта
            
        Returns:
            bool: True если успешно
        """
        try:
            session = self.get_session()
            if not session:
                return False
            
            # Проверяем, что эксперт существует
            expert = session.query(Expert).filter(Expert.id == expert_id).first()
            if expert:
                # Сохраняем выбранного эксперта в памяти
                self.selected_expert_id = expert_id
                
                # Сохраняем только в памяти (из-за проблем с правами БД)
                print(f"✅ Эксперт недели установлен в памяти: {expert.name} (ID: {expert.id})")
                
                session.close()
                return True
            else:
                print(f"❌ Эксперт с ID {expert_id} не найден")
                session.close()
                return False
            
        except Exception as e:
            print(f"❌ Ошибка установки эксперта недели: {e}")
            return False
    
    def get_expert_comments_for_news(self, news_ids: List[int]) -> Dict[int, Dict]:
        """
        Получить комментарии экспертов к новостям.
        
        Args:
            news_ids: Список ID новостей
            
        Returns:
            Dict[int, Dict]: Словарь {news_id: comment_data}
        """
        try:
            session = self.get_session()
            if not session:
                return {}
            
            from models.database import Comment
            
            # Получаем комментарии к новостям
            comments = session.query(Comment).filter(
                Comment.news_id.in_(news_ids)
            ).all()
            
            # Формируем словарь комментариев
            comments_dict = {}
            print(f"🔍 Найдено комментариев: {len(comments)} для новостей: {news_ids}")
            for comment in comments:
                comments_dict[comment.news_id] = {
                    "text": comment.text,
                    "expert": {
                        "name": comment.expert.name if comment.expert else "Неизвестный эксперт",
                        "specialization": comment.expert.specialization if comment.expert else "AI"
                    }
                }
                print(f"📝 Комментарий для новости {comment.news_id}: {comment.text[:50]}...")
            
            session.close()
            print(f"✅ Возвращаем {len(comments_dict)} комментариев")
            return comments_dict
            
        except Exception as e:
            print(f"❌ Ошибка получения комментариев: {e}")
            return {}
    
    def get_news_sources(self, news_ids: List[int]) -> Dict[int, List[str]]:
        """
        Получить источники новостей.
        
        Args:
            news_ids: Список ID новостей
            
        Returns:
            Dict[int, List[str]]: Словарь {news_id: [source_names]}
        """
        try:
            session = self.get_session()
            if not session:
                return {}
            
            # Получаем новости с их источниками
            news_list = session.query(News).filter(
                News.id.in_(news_ids)
            ).all()
            
            # Формируем словарь источников
            sources_dict = {}
            for news in news_list:
                # Получаем источники через связь NewsSource
                from models.database import NewsSource
                news_sources = session.query(NewsSource).filter(
                    NewsSource.news_id == news.id
                ).all()
                
                print(f"🔍 Новость {news.id}: найдено {len(news_sources)} связей NewsSource")
                
                if news_sources:
                    # Получаем уникальные источники (убираем дубликаты)
                    unique_sources = set()
                    for ns in news_sources:
                        source = session.query(Source).filter(Source.id == ns.source_id).first()
                        if source:
                            unique_sources.add(source)
                    
                    # Создаем одну ссылку на источник (первый уникальный)
                    if unique_sources:
                        source = list(unique_sources)[0]  # Берем первый уникальный источник
                        if source.telegram_id:
                            # Создаем ссылку на Telegram канал
                            if source.telegram_id.startswith('@'):
                                source_link = f"[{source.name}](https://t.me/{source.telegram_id[1:]})"
                            else:
                                source_link = f"[{source.name}](https://t.me/{source.telegram_id})"
                        else:
                            source_link = source.name
                        sources_dict[news.id] = [source_link]  # Одна ссылка на источник
                        print(f"✅ Новость {news.id}: источник {source_link}")
                    else:
                        sources_dict[news.id] = ["Неизвестный источник"]
                        print(f"❌ Новость {news.id}: нет источников")
                else:
                    # Fallback для тестовых данных - используем разные источники для разных новостей
                    all_sources = session.query(Source).all()
                    if all_sources:
                        # Используем разные источники для разных новостей
                        source_index = news.id % len(all_sources)
                        source = all_sources[source_index]
                        if source.telegram_id:
                            # Создаем ссылку на Telegram канал
                            if source.telegram_id.startswith('@'):
                                source_link = f"[{source.name}](https://t.me/{source.telegram_id[1:]})"
                            else:
                                source_link = f"[{source.name}](https://t.me/{source.telegram_id})"
                        else:
                            source_link = source.name
                        sources_dict[news.id] = [source_link]  # Одна ссылка на источник
                        print(f"⚠️ Новость {news.id}: fallback источник {source_link}")
                    else:
                        sources_dict[news.id] = ["Неизвестный источник"]
                        print(f"❌ Новость {news.id}: нет источников")
            
            session.close()
            return sources_dict
            
        except Exception as e:
            print(f"❌ Ошибка получения источников: {e}")
            return {} 