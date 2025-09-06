#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Expert Choice Service - сервис для выбора эксперта через inline кнопки.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from telegram import InlineKeyboardButton

logger = logging.getLogger(__name__)

@dataclass
class Expert:
    """Эксперт для выбора."""
    id: int
    name: str
    specialization: str
    telegram_id: Optional[str] = None
    is_test: bool = False

class ExpertChoiceService:
    """
    Сервис для выбора эксперта через inline кнопки.
    """
    
    def __init__(self):
        """Инициализация сервиса."""
        # Список экспертов согласно требованиям
        self.experts = [
            Expert(id=1, name="Рамиль Зайнеев", specialization="AI/ML", is_test=False),
            Expert(id=2, name="Станислав Маслов", specialization="Разработка", is_test=False),
            Expert(id=3, name="Степан Игонин", specialization="Аналитика", is_test=False),
            Expert(id=4, name="Я (тестовый эксперт)", specialization="Тестирование", telegram_id="1326944316", is_test=True)
        ]
        
        logger.info("✅ ExpertChoiceService инициализирован")
    
    def get_experts_for_choice(self) -> List[Expert]:
        """
        Получает список экспертов для выбора.
        
        Returns:
            List[Expert]: Список экспертов
        """
        return self.experts
    
    def create_expert_choice_buttons(self) -> List[List[InlineKeyboardButton]]:
        """
        Создает inline кнопки для выбора эксперта.
        
        Returns:
            List[List[InlineKeyboardButton]]: Матрица кнопок
        """
        buttons = []
        
        for expert in self.experts:
            if expert.is_test:
                # Тестовый эксперт - работает
                callback_data = f"select_expert_{expert.id}"
            else:
                # Реальные эксперты - пока не работают
                callback_data = f"expert_unavailable_{expert.id}"
            
            buttons.append([
                InlineKeyboardButton(
                    f"👨‍💻 {expert.name}",
                    callback_data=callback_data
                )
            ])
        
        return buttons
    
    def get_expert_by_id(self, expert_id: int) -> Optional[Expert]:
        """
        Получает эксперта по ID.
        
        Args:
            expert_id: ID эксперта
            
        Returns:
            Optional[Expert]: Эксперт или None
        """
        for expert in self.experts:
            if expert.id == expert_id:
                return expert
        return None
    
    def is_test_expert(self, expert_id: int) -> bool:
        """
        Проверяет, является ли эксперт тестовым.
        
        Args:
            expert_id: ID эксперта
            
        Returns:
            bool: True если тестовый эксперт
        """
        expert = self.get_expert_by_id(expert_id)
        return expert.is_test if expert else False
