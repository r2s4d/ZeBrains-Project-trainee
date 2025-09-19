#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Expert Choice Service - сервис для выбора эксперта через inline кнопки.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from telegram import InlineKeyboardButton
from src.config import config
from src.models import SessionLocal, Expert as ExpertModel

logger = logging.getLogger(__name__)

@dataclass
class Expert:
    """Эксперт для выбора."""
    id: int
    name: str
    specialization: str
    telegram_id: Optional[str] = None

class ExpertChoiceService:
    """
    Сервис для выбора эксперта через inline кнопки.
    Динамически загружает экспертов из БД.
    """
    
    def __init__(self):
        """Инициализация сервиса."""
        self.db = SessionLocal()
        logger.info("✅ ExpertChoiceService инициализирован")
    
    def get_experts_for_choice(self) -> List[Expert]:
        """
        Получает список экспертов для выбора из БД.
        
        Returns:
            List[Expert]: Список экспертов
        """
        try:
            # Получаем активных экспертов из БД
            experts_from_db = self.db.query(ExpertModel).filter(ExpertModel.is_active == True).all()
            
            experts = []
            for expert_db in experts_from_db:
                expert = Expert(
                    id=expert_db.id,
                    name=expert_db.name,
                    specialization=expert_db.specialization,
                    telegram_id=expert_db.telegram_id
                )
                experts.append(expert)
                
            logger.info(f"📋 Загружено {len(experts)} экспертов из БД")
            return experts
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки экспертов из БД: {e}")
            return []
    
    def create_expert_choice_buttons(self) -> List[List[InlineKeyboardButton]]:
        """
        Создает inline кнопки для выбора эксперта динамически из БД.
        
        Returns:
            List[List[InlineKeyboardButton]]: Матрица кнопок
        """
        buttons = []
        experts = self.get_experts_for_choice()
        
        for expert in experts:
            # Все эксперты доступны для выбора
            callback_data = f"select_expert_{expert.id}"
            button_text = f"👨‍💻 {expert.name}"
            
            buttons.append([
                InlineKeyboardButton(
                    button_text,
                    callback_data=callback_data
                )
            ])
        
        logger.info(f"🔘 Создано {len(buttons)} кнопок выбора экспертов")
        return buttons
    
    def get_expert_by_id(self, expert_id: int) -> Optional[Expert]:
        """
        Получает эксперта по ID из БД.
        
        Args:
            expert_id: ID эксперта
            
        Returns:
            Optional[Expert]: Эксперт или None
        """
        try:
            expert_db = self.db.query(ExpertModel).filter(ExpertModel.id == expert_id).first()
            
            if expert_db:
                return Expert(
                    id=expert_db.id,
                    name=expert_db.name,
                    specialization=expert_db.specialization,
                    telegram_id=expert_db.telegram_id
                )
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения эксперта {expert_id}: {e}")
            return None
    
    def __del__(self):
        """Закрытие соединения с БД при удалении объекта."""
        try:
            if hasattr(self, 'db'):
                self.db.close()
        except:
            pass
    
