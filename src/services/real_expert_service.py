"""
RealExpertService - сервис для работы с реальными экспертами

Этот сервис заменяет AI на реальных экспертов-людей.
Он управляет назначением экспертов к новостям, отправкой уведомлений
и сбором комментариев от экспертов.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.models.database import Expert, Comment, News, Curator
from src.services.database_service import DatabaseService


class RealExpertService:
    """
    Сервис для работы с реальными экспертами.
    
    Основные функции:
    - Назначение экспертов к новостям
    - Отправка уведомлений экспертам
    - Сбор комментариев от экспертов
    - Управление статусами заданий
    """
    
    def __init__(self, database_service: DatabaseService):
        """
        Инициализация сервиса.
        
        Args:
            database_service: Сервис для работы с базой данных
        """
        self.database_service = database_service
    
    def get_available_experts(self, specialization: Optional[str] = None) -> List[Expert]:
        """
        Получить список доступных экспертов.
        
        Args:
            specialization: Специализация экспертов (например, "AI", "ML", "NLP")
            
        Returns:
            Список активных экспертов
        """
        with self.database_service.get_session() as session:
            query = session.query(Expert).filter(Expert.is_active == True)
            
            if specialization:
                query = query.filter(Expert.specialization == specialization)
            
            return query.all()
    
    def assign_expert_to_news(self, news_id: int, expert_id: int) -> Dict[str, Any]:
        """
        Назначить эксперта к новости.
        
        Args:
            news_id: ID новости
            expert_id: ID эксперта
            
        Returns:
            Словарь с информацией о назначении
        """
        with self.database_service.get_session() as session:
            # Проверяем, что новость и эксперт существуют
            news = session.query(News).filter(News.id == news_id).first()
            expert = session.query(Expert).filter(Expert.id == expert_id).first()
            
            if not news:
                raise ValueError(f"Новость с ID {news_id} не найдена")
            
            if not expert:
                raise ValueError(f"Эксперт с ID {expert_id} не найден")
            
            if not expert.is_active:
                raise ValueError(f"Эксперт {expert.name} неактивен")
            
            # Проверяем, не назначен ли уже эксперт к этой новости
            existing_comment = session.query(Comment).filter(
                and_(Comment.news_id == news_id, Comment.expert_id == expert_id)
            ).first()
            
            if existing_comment:
                return {
                    "status": "already_assigned",
                    "message": f"Эксперт {expert.name} уже назначен к новости {news_id}",
                    "expert_name": expert.name,
                    "news_title": news.title
                }
            
            # Создаем новый комментарий со статусом "pending"
            comment = Comment(
                news_id=news_id,
                expert_id=expert_id,
                text="",  # Пока пустой, эксперт заполнит
                created_at=datetime.utcnow()
            )
            
            session.add(comment)
            session.commit()
            
            return {
                "status": "assigned",
                "message": f"Эксперт {expert.name} назначен к новости",
                "expert_name": expert.name,
                "expert_telegram_id": expert.telegram_id,
                "news_title": news.title,
                "comment_id": comment.id
            }
    
    def get_pending_assignments(self, expert_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Получить список ожидающих назначений.
        
        Args:
            expert_id: ID конкретного эксперта (если None, то все эксперты)
            
        Returns:
            Список назначений с информацией о новостях и экспертах
        """
        with self.database_service.get_session() as session:
            query = session.query(Comment, News, Expert).join(
                News, Comment.news_id == News.id
            ).join(
                Expert, Comment.expert_id == Expert.id
            ).filter(
                Comment.text == ""  # Пустой текст означает, что комментарий еще не написан
            )
            
            if expert_id:
                query = query.filter(Comment.expert_id == expert_id)
            
            results = query.all()
            
            assignments = []
            for comment, news, expert in results:
                assignments.append({
                    "comment_id": comment.id,
                    "news_id": news.id,
                    "news_title": news.title,
                    "news_content": news.content[:200] + "..." if len(news.content) > 200 else news.content,
                    "expert_id": expert.id,
                    "expert_name": expert.name,
                    "assigned_at": comment.created_at,
                    "days_since_assignment": (datetime.utcnow() - comment.created_at).days
                })
            
            return assignments
    
    def submit_expert_comment(self, comment_id: int, expert_telegram_id: str, comment_text: str) -> Dict[str, Any]:
        """
        Эксперт отправляет свой комментарий.
        
        Args:
            comment_id: ID комментария
            expert_telegram_id: Telegram ID эксперта (для проверки)
            comment_text: Текст комментария
            
        Returns:
            Словарь с результатом операции
        """
        with self.database_service.get_session() as session:
            # Находим комментарий и проверяем права эксперта
            comment = session.query(Comment).filter(Comment.id == comment_id).first()
            
            if not comment:
                raise ValueError(f"Комментарий с ID {comment_id} не найден")
            
            # Проверяем, что комментарий принадлежит этому эксперту
            expert = session.query(Expert).filter(
                and_(Expert.id == comment.expert_id, Expert.telegram_id == expert_telegram_id)
            ).first()
            
            if not expert:
                raise ValueError("У вас нет прав для редактирования этого комментария")
            
            # Обновляем комментарий
            comment.text = comment_text
            comment.updated_at = datetime.utcnow()
            
            session.commit()
            
            return {
                "status": "submitted",
                "message": "Комментарий успешно отправлен",
                "comment_id": comment.id,
                "expert_name": expert.name
            }
    
    def get_expert_statistics(self, expert_id: int) -> Dict[str, Any]:
        """
        Получить статистику эксперта.
        
        Args:
            expert_id: ID эксперта
            
        Returns:
            Словарь со статистикой
        """
        with self.database_service.get_session() as session:
            expert = session.query(Expert).filter(Expert.id == expert_id).first()
            
            if not expert:
                raise ValueError(f"Эксперт с ID {expert_id} не найден")
            
            # Подсчитываем комментарии
            total_comments = session.query(Comment).filter(Comment.expert_id == expert_id).count()
            completed_comments = session.query(Comment).filter(
                and_(Comment.expert_id == expert_id, Comment.text != "")
            ).count()
            pending_comments = total_comments - completed_comments
            
            # Среднее время выполнения
            completed_comments_data = session.query(Comment).filter(
                and_(Comment.expert_id == expert_id, Comment.text != "")
            ).all()
            
            avg_time = 0
            if completed_comments_data:
                total_time = sum([
                    (comment.updated_at - comment.created_at).total_seconds() / 3600  # в часах
                    for comment in completed_comments_data
                    if comment.updated_at and comment.created_at
                ])
                avg_time = total_time / len(completed_comments_data)
            
            return {
                "expert_name": expert.name,
                "specialization": expert.specialization,
                "is_active": expert.is_active,
                "total_assignments": total_comments,
                "completed_assignments": completed_comments,
                "pending_assignments": pending_comments,
                "completion_rate": (completed_comments / total_comments * 100) if total_comments > 0 else 0,
                "average_completion_time_hours": round(avg_time, 2)
            }
    
    def auto_assign_experts(self, news_id: int) -> Dict[str, Any]:
        """
        Автоматически назначить эксперта к новости на основе специализации.
        
        Args:
            news_id: ID новости
            
        Returns:
            Словарь с результатом назначения
        """
        with self.database_service.get_session() as session:
            news = session.query(News).filter(News.id == news_id).first()
            
            if not news:
                raise ValueError(f"Новость с ID {news_id} не найдена")
            
            # Простая логика: анализируем заголовок и содержимое новости
            # для определения специализации
            text_for_analysis = f"{news.title} {news.content}".lower()
            
            # Определяем специализацию на основе ключевых слов
            specialization = self._determine_specialization(text_for_analysis)
            
            # Ищем подходящего эксперта
            available_experts = session.query(Expert).filter(
                and_(
                    Expert.is_active == True,
                    Expert.specialization == specialization
                )
            ).all()
            
            if not available_experts:
                # Если нет экспертов с нужной специализацией, берем любого активного
                available_experts = session.query(Expert).filter(Expert.is_active == True).all()
            
            if not available_experts:
                return {
                    "status": "no_experts_available",
                    "message": "Нет доступных экспертов"
                }
            
            # Выбираем эксперта с наименьшей нагрузкой
            best_expert = self._select_best_expert(session, available_experts)
            
            # Назначаем эксперта
            return self.assign_expert_to_news(news_id, best_expert.id)
    
    def _determine_specialization(self, text: str) -> str:
        """
        Определить специализацию на основе текста новости.
        
        Args:
            text: Текст новости
            
        Returns:
            Специализация ("AI", "ML", "NLP", etc.)
        """
        text_lower = text.lower()
        
        # Проверяем в порядке приоритета
        if any(word in text_lower for word in ["gpt", "openai", "chatbot", "language model", "nlp", "natural language"]):
            return "NLP"
        elif any(word in text_lower for word in ["neural", "deep learning", "cnn", "rnn", "machine learning", "ml"]):
            return "ML"
        elif any(word in text_lower for word in ["computer vision", "image", "video", "cv", "компьютерного зрения", "изображения", "видео"]):
            return "CV"
        elif any(word in text_lower for word in ["ai", "artificial intelligence", "automation"]):
            return "AI"
        else:
            return "AI"  # По умолчанию
    
    def _select_best_expert(self, session: Session, experts: List[Expert]) -> Expert:
        """
        Выбрать лучшего эксперта на основе нагрузки.
        
        Args:
            session: Сессия базы данных
            experts: Список доступных экспертов
            
        Returns:
            Эксперт с наименьшей нагрузкой
        """
        best_expert = None
        min_load = float('inf')
        
        for expert in experts:
            # Подсчитываем количество активных назначений
            pending_count = session.query(Comment).filter(
                and_(Comment.expert_id == expert.id, Comment.text == "")
            ).count()
            
            if pending_count < min_load:
                min_load = pending_count
                best_expert = expert
        
        return best_expert or experts[0]  # Fallback на первого эксперта 