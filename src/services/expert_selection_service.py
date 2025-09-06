#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Expert Selection Service - сервис для выбора ОДНОГО эксперта на весь модерированный дайджест.
Эксперт будет анализировать все одобренные новости сразу.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ExpertStatus(Enum):
    """Статусы экспертов."""
    AVAILABLE = "available"           # Доступен для работы
    BUSY = "busy"                     # Занят другими заданиями
    UNAVAILABLE = "unavailable"       # Недоступен

@dataclass
class Expert:
    """Эксперт для анализа новостей."""
    id: int
    name: str
    specialization: str
    status: ExpertStatus
    current_workload: int
    max_workload: int
    rating: float
    response_time_hours: float
    telegram_id: Optional[str] = None

@dataclass
class ExpertAssignment:
    """Назначение эксперта на дайджест."""
    assignment_id: str
    expert_id: int
    expert_name: str
    digest_id: str
    news_count: int
    assignment_date: datetime
    deadline: datetime
    status: str = "assigned"  # assigned, in_progress, completed

class ExpertSelectionService:
    """
    Сервис для выбора ОДНОГО эксперта на весь модерированный дайджест.
    """
    
    def __init__(self, database_service, notification_service):
        """
        Инициализация сервиса.
        
        Args:
            database_service: Сервис для работы с базой данных
            notification_service: Сервис уведомлений
        """
        self.db = database_service
        self.notification = notification_service
        
        logger.info("✅ ExpertSelectionService инициализирован")
    
    async def get_available_experts(self) -> List[Expert]:
        """
        Получает список доступных экспертов.
        
        Returns:
            List[Expert]: Список доступных экспертов
        """
        try:
            # В реальной версии получаем из БД
            # Пока используем моковые данные
            experts = [
                Expert(
                    id=1,
                    name="Иван Петров",
                    specialization="AI/ML, Искусственный интеллект",
                    status=ExpertStatus.AVAILABLE,
                    current_workload=2,
                    max_workload=5,
                    rating=4.8,
                    response_time_hours=3.5,
                    telegram_id="@ivan_petrov"
                ),
                Expert(
                    id=2,
                    name="Мария Сидорова",
                    specialization="Технологический анализ, Стартапы",
                    status=ExpertStatus.AVAILABLE,
                    current_workload=1,
                    max_workload=5,
                    rating=4.6,
                    response_time_hours=5.0,
                    telegram_id="@maria_sidorova"
                ),
                Expert(
                    id=3,
                    name="Алексей Козлов",
                    specialization="Корпоративные технологии, Microsoft, Google",
                    status=ExpertStatus.AVAILABLE,
                    current_workload=3,
                    max_workload=5,
                    rating=4.7,
                    response_time_hours=4.0,
                    telegram_id="@alex_kozlov"
                )
            ]
            
            # Фильтруем только доступных экспертов
            available_experts = [
                expert for expert in experts
                if expert.status == ExpertStatus.AVAILABLE and expert.current_workload < expert.max_workload
            ]
            
            # Сортируем по рейтингу и загрузке
            available_experts.sort(key=lambda x: (x.rating, -x.current_workload), reverse=True)
            
            logger.info(f"✅ Найдено {len(available_experts)} доступных экспертов")
            return available_experts
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения доступных экспертов: {e}")
            return []
    
    async def suggest_experts_for_digest(self, news_count: int) -> List[Expert]:
        """
        Предлагает экспертов для дайджеста с учетом количества новостей.
        
        Args:
            news_count: Количество новостей в дайджесте
            
        Returns:
            List[Expert]: Список подходящих экспертов
        """
        try:
            available_experts = await self.get_available_experts()
            
            # Фильтруем экспертов, которые могут взять дополнительную нагрузку
            suitable_experts = []
            for expert in available_experts:
                # Проверяем, может ли эксперт взять дополнительную нагрузку
                if expert.current_workload + news_count <= expert.max_workload:
                    suitable_experts.append(expert)
            
            # Сортируем по приоритету (рейтинг, время ответа, загрузка)
            suitable_experts.sort(key=lambda x: (
                x.rating,
                x.response_time_hours,
                x.current_workload
            ), reverse=True)
            
            logger.info(f"✅ Предложено {len(suitable_experts)} подходящих экспертов для {news_count} новостей")
            return suitable_experts
            
        except Exception as e:
            logger.error(f"❌ Ошибка предложения экспертов: {e}")
            return []
    
    async def assign_expert_to_digest(self, expert_id: int, digest_id: str, news_count: int) -> Optional[ExpertAssignment]:
        """
        Назначает эксперта на дайджест.
        
        Args:
            expert_id: ID эксперта
            digest_id: ID дайджеста
            news_count: Количество новостей
            
        Returns:
            Optional[ExpertAssignment]: Назначение эксперта или None
        """
        try:
            # Получаем эксперта
            available_experts = await self.get_available_experts()
            expert = next((e for e in available_experts if e.id == expert_id), None)
            
            if not expert:
                logger.error(f"❌ Эксперт {expert_id} не найден или недоступен")
                return None
            
            # Проверяем, может ли эксперт взять задание
            if expert.current_workload + news_count > expert.max_workload:
                logger.error(f"❌ Эксперт {expert.name} не может взять {news_count} новостей (загрузка: {expert.current_workload}/{expert.max_workload})")
                return None
            
            # Создаем назначение
            assignment = ExpertAssignment(
                assignment_id=f"assign_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                expert_id=expert.id,
                expert_name=expert.name,
                digest_id=digest_id,
                news_count=news_count,
                assignment_date=datetime.now(),
                deadline=datetime.now().replace(hour=18, minute=0, second=0, microsecond=0)  # Дедлайн 18:00
            )
            
            # Обновляем загрузку эксперта
            expert.current_workload += news_count
            
            logger.info(f"✅ Эксперт {expert.name} назначен на дайджест {digest_id} ({news_count} новостей)")
            return assignment
            
        except Exception as e:
            logger.error(f"❌ Ошибка назначения эксперта {expert_id}: {e}")
            return None
    
    async def notify_expert(self, assignment: ExpertAssignment) -> bool:
        """
        Уведомляет эксперта о новом задании.
        
        Args:
            assignment: Назначение эксперта
            
        Returns:
            bool: Успешность уведомления
        """
        try:
            # В реальной версии отправляем уведомление через Telegram
            message = f"""
🔔 НОВОЕ ЗАДАНИЕ ДЛЯ ЭКСПЕРТА

📰 Дайджест: {assignment.digest_id}
📊 Новостей для анализа: {assignment.news_count}
⏰ Дедлайн: {assignment.deadline.strftime('%d.%m.%Y %H:%M')}

Пожалуйста, проанализируйте все новости и предоставьте экспертное мнение.
            """.strip()
            
            # Логируем уведомление
            logger.info(f"📤 Уведомление отправлено эксперту {assignment.expert_name}: {message[:100]}...")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления эксперта: {e}")
            return False
    
    def get_assignment_status(self, assignment: ExpertAssignment) -> Dict[str, Any]:
        """
        Получает статус назначения эксперта.
        
        Args:
            assignment: Назначение эксперта
            
        Returns:
            Dict: Статус назначения
        """
        try:
            return {
                "assignment_id": assignment.assignment_id,
                "expert_name": assignment.expert_name,
                "digest_id": assignment.digest_id,
                "news_count": assignment.news_count,
                "assignment_date": assignment.assignment_date,
                "deadline": assignment.deadline,
                "status": assignment.status,
                "time_remaining": (assignment.deadline - datetime.now()).total_seconds() / 3600 if assignment.deadline > datetime.now() else 0
            }
        except Exception as e:
            logger.error(f"❌ Ошибка получения статуса назначения: {e}")
            return {"error": str(e)}
