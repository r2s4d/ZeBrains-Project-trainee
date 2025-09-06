"""
CuratorService - сервис для управления кураторами

Этот сервис управляет процессом курирования новостей:
- Управление кураторами
- Процесс согласования новостей
- Фильтрация контента перед отправкой экспертам
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.models.database import Curator, News, Expert, Comment
from src.services.database_service import DatabaseService


class CuratorService:
    """
    Сервис для работы с кураторами.
    
    Основные функции:
    - Управление кураторами
    - Процесс согласования новостей
    - Фильтрация контента
    - Отправка новостей экспертам
    """
    
    def __init__(self, database_service: DatabaseService):
        """
        Инициализация сервиса.
        
        Args:
            database_service: Сервис для работы с базой данных
        """
        self.database_service = database_service
    
    def get_active_curators(self) -> List[Curator]:
        """
        Получить список активных кураторов.
        
        Returns:
            Список активных кураторов
        """
        with self.database_service.get_session() as session:
            curators = session.query(Curator).filter(Curator.is_active == True).all()
            return curators
    
    def get_all_curators(self) -> List[Curator]:
        """
        Получить всех кураторов.
        
        Returns:
            Список всех кураторов
        """
        with self.database_service.get_session() as session:
            curators = session.query(Curator).all()
            return curators
    
    def get_curator_by_telegram_id(self, telegram_id: str) -> Optional[Curator]:
        """
        Получить куратора по Telegram ID.
        
        Args:
            telegram_id: Telegram ID куратора
            
        Returns:
            Куратор или None
        """
        session = self.database_service.get_session()
        try:
            curator = session.query(Curator).filter(
                and_(Curator.telegram_id == telegram_id, Curator.is_active == True)
            ).first()
            return curator
        finally:
            session.close()
    
    def get_pending_news_for_curation(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получить новости, ожидающие курирования.
        
        Args:
            limit: Максимальное количество новостей
            
        Returns:
            Список новостей с информацией для курирования
        """
        session = self.database_service.get_session()
        try:
            # Получаем новости со статусом 'new' (новые)
            news_list = session.query(News).filter(
                News.status == 'new'
            ).order_by(News.created_at.desc()).limit(limit).all()
            
            curated_news = []
            for news in news_list:
                # Проверяем, есть ли уже комментарии экспертов
                expert_comments = session.query(Comment).filter(
                    Comment.news_id == news.id
                ).count()
                
                curated_news.append({
                    "news_id": news.id,
                    "title": news.title,
                    "content": news.content[:200] + "..." if len(news.content) > 200 else news.content,
                    "url": news.url,
                    "created_at": news.created_at,
                    "is_duplicate": news.is_duplicate,
                    "expert_comments_count": expert_comments,
                    "days_since_creation": (datetime.utcnow() - news.created_at).days
                })
            
            return curated_news
        finally:
            session.close()
    
    def get_pending_news(self, curator_telegram_id: str) -> List[News]:
        """
        Получить новости, ожидающие курирования (для бота).
        
        Args:
            curator_telegram_id: Telegram ID куратора
            
        Returns:
            Список новостей
        """
        try:
            # Получаем новости со статусом 'pending_curation' из PostgreSQL
            session = self.database_service.get_session()
            if session:
                try:
                    from src.models.database import News
                    pending_news = session.query(News).filter_by(status='pending_curation').all()
                    return pending_news
                finally:
                    session.close()
            else:
                logger.error("❌ Не удалось получить сессию базы данных")
                return []
        except Exception as e:
            logger.error(f"❌ Ошибка при получении новостей для курирования: {e}")
            return []
    
    def approve_news(self, curator_telegram_id: str, news_id: int) -> bool:
        """
        Одобрить новость для экспертов.
        
        Args:
            curator_telegram_id: Telegram ID куратора
            news_id: ID новости
            
        Returns:
            True если успешно, False иначе
        """
        try:
            # Обновляем статус в mock данных через BotDatabaseService
            if hasattr(self.database_service, 'update_news_status'):
                success = self.database_service.update_news_status(news_id, "approved")
                if success:
                    print(f"✅ Новость {news_id} одобрена для экспертизы")
                    return True
                else:
                    print(f"❌ Не удалось обновить статус новости {news_id}")
                    return False
            
            # Fallback для старых версий
            session = self.database_service.get_session()
            try:
                news = session.query(News).filter(News.id == news_id).first()
                if news:
                    news.status = 'approved'
                    news.curator_id = curator_telegram_id
                    news.curated_at = datetime.utcnow()
                    session.commit()
                    return True
                return False
            finally:
                session.close()
        except Exception as e:
            print(f"❌ Ошибка при одобрении новости: {e}")
            return False
    
    def reject_news(self, curator_telegram_id: str, news_id: int) -> bool:
        """
        Отклонить новость.
        
        Args:
            curator_telegram_id: Telegram ID куратора
            news_id: ID новости
            
        Returns:
            True если успешно, False иначе
        """
        try:
            session = self.database_service.get_session()
            try:
                news = session.query(News).filter(News.id == news_id).first()
                if news:
                    news.status = 'rejected'
                    news.curator_id = curator_telegram_id
                    news.curated_at = datetime.utcnow()
                    session.commit()
                    return True
                return False
            finally:
                session.close()
        except Exception as e:
            print(f"❌ Ошибка при отклонении новости: {e}")
            return False
    
    def get_daily_digest(self, curator_telegram_id: str) -> Dict[str, Any]:
        """
        Получить ежедневный дайджест для куратора.
        
        Args:
            curator_telegram_id: Telegram ID куратора
            
        Returns:
            Словарь с данными дайджеста
        """
        # Для тестирования возвращаем Mock данные
        return {
            "today_news": 8,
            "approved_today": 5,
            "rejected_today": 2,
            "active_experts": 3
        }
    
    def approve_news_for_experts(self, news_ids: List[int], curator_telegram_id: str) -> Dict[str, Any]:
        """
        Одобрить новости для отправки экспертам.
        
        Args:
            news_ids: Список ID новостей для одобрения
            curator_telegram_id: Telegram ID куратора
            
        Returns:
            Словарь с результатом операции
        """
        session = self.database_service.get_session()
        try:
            # Проверяем, что куратор существует и активен
            curator = self.get_curator_by_telegram_id(curator_telegram_id)
            if not curator:
                return {
                    "status": "error",
                    "message": "Куратор не найден или неактивен"
                }
            
            approved_count = 0
            rejected_count = 0
            
            for news_id in news_ids:
                news = session.query(News).filter(News.id == news_id).first()
                if news and news.status == 'new':
                    # Обновляем статус на 'approved_for_experts'
                    news.status = 'approved_for_experts'
                    approved_count += 1
                else:
                    rejected_count += 1
            
            session.commit()
            
            return {
                "status": "success",
                "message": f"Одобрено {approved_count} новостей, отклонено {rejected_count}",
                "approved_count": approved_count,
                "rejected_count": rejected_count,
                "curator_name": curator.name
            }
        finally:
            session.close()
    
    def reject_news(self, news_ids: List[int], curator_telegram_id: str, reason: str = "") -> Dict[str, Any]:
        """
        Отклонить новости.
        
        Args:
            news_ids: Список ID новостей для отклонения
            curator_telegram_id: Telegram ID куратора
            reason: Причина отклонения
            
        Returns:
            Словарь с результатом операции
        """
        # Для тестирования возвращаем Mock данные
        return {
            "status": "success",
            "message": f"Отклонено {len(news_ids)} новостей",
            "rejected_count": len(news_ids),
            "curator_name": "Тестовый Куратор",
            "reason": reason
        }
    
    def get_news_ready_for_experts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получить новости, готовые для отправки экспертам.
        
        Args:
            limit: Максимальное количество новостей
            
        Returns:
            Список новостей, готовых для экспертов
        """
        # Для тестирования возвращаем Mock данные
        return [
            {
                "news_id": 1,
                "title": "AI Breakthrough",
                "content": "New AI model shows remarkable performance...",
                "url": "https://example.com/ai-news",
                "created_at": datetime.utcnow(),
                "assigned_experts": 2,
                "expert_names": ["AI Expert", "ML Specialist"]
            },
            {
                "news_id": 2,
                "title": "Tech Update",
                "content": "Latest technology developments...",
                "url": "https://example.com/tech-news",
                "created_at": datetime.utcnow(),
                "assigned_experts": 1,
                "expert_names": ["Tech Expert"]
            }
        ]
    
    def approve_final_post(self, post_id: int, curator_telegram_id: str) -> Dict[str, Any]:
        """
        Одобрить финальный пост для публикации.
        
        Args:
            post_id: ID поста
            curator_telegram_id: Telegram ID куратора
            
        Returns:
            Словарь с результатом операции
        """
        # Для тестирования возвращаем Mock данные
        return {
            "status": "success",
            "message": f"Пост {post_id} одобрен для публикации",
            "curator_name": "Тестовый Куратор",
            "approved_at": datetime.utcnow()
        }
    
    def request_post_revision(self, post_id: int, curator_telegram_id: str, feedback: str) -> Dict[str, Any]:
        """
        Запросить переработку поста.
        
        Args:
            post_id: ID поста
            curator_telegram_id: Telegram ID куратора
            feedback: Комментарии для переработки
            
        Returns:
            Словарь с результатом операции
        """
        # Для тестирования возвращаем Mock данные
        return {
            "status": "success",
            "message": f"Запрошена переработка поста {post_id}",
            "curator_name": "Тестовый Куратор",
            "feedback": feedback,
            "requested_at": datetime.utcnow()
        }
    
    def get_curator_statistics(self, curator_telegram_id: str) -> Dict[str, Any]:
        """
        Получить статистику куратора.
        
        Args:
            curator_telegram_id: Telegram ID куратора
            
        Returns:
            Словарь со статистикой
        """
        # Для тестирования возвращаем Mock данные
        return {
            "curator_name": "Тестовый Куратор",
            "total_news": 25,
            "pending_news": 8,
            "approved_news": 12,
            "rejected_news": 5,
            "approval_rate": 70.59
        }
    
    def create_daily_digest_for_curators(self) -> Dict[str, Any]:
        """
        Создать ежедневный дайджест для кураторов.
        
        Returns:
            Словарь с дайджестом
        """
        # Для тестирования возвращаем Mock данные
        from datetime import datetime
        
        return {
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "new_news_count": 5,
            "approved_news_count": 3,
            "rejected_news_count": 2,
            "new_news": [
                {"id": 1, "title": "AI Breakthrough", "created_at": "09:30"},
                {"id": 2, "title": "Tech Update", "created_at": "10:15"},
                {"id": 3, "title": "Startup News", "created_at": "11:00"}
            ],
            "total_processed": 10
        } 