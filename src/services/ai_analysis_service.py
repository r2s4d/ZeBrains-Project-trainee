#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI анализ новостей с использованием OpenAI API.
Обновленная версия: объединенный промпт для саммари и анализа.
"""

import logging
import os
from datetime import datetime
from typing import Optional
from dataclasses import dataclass
from openai import OpenAI
from src.config import config

logger = logging.getLogger(__name__)

class AIAnalysisService:
    """
    Сервис для AI анализа новостей с использованием OpenAI API.
    Обновленная версия: объединенный промпт для саммари и анализа.
    """
    
    def __init__(self):
        """Инициализация AI сервиса."""
        # Проверяем доступность ProxyAPI
        self.proxy_url = config.ai.proxy_url
        self.proxy_api_key = config.ai.proxy_api_key
        
        if self.proxy_url and self.proxy_api_key:
            logger.info("🚀 Используем ProxyAPI для AI анализа")
            self.use_proxy = True
        else:
            logger.warning("⚠️ ProxyAPI не настроен, AI анализ недоступен")
            self.use_proxy = False
        
        # OpenAI клиент для работы через ProxyAPI
        self.client = None
        if self.use_proxy:
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=self.proxy_api_key,
                    base_url=self.proxy_url
                )
                logger.info("✅ OpenAI клиент через ProxyAPI инициализирован")
                
                # Проверяем доступность модели
                try:
                    models_response = self.client.models.list()
                    available_models = [model.id for model in models_response.data]
                    logger.info(f"📋 Доступные модели: {available_models}")
                    
                    preferred_model = config.ai.model
                    if preferred_model in available_models:
                        logger.info(f"✅ Модель {preferred_model} доступна")
                    else:
                        logger.warning(f"⚠️ Модель {preferred_model} недоступна, доступные: {available_models}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось проверить доступные модели: {e}")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации OpenAI клиента: {e}")
                self.client = None
        
        
        logger.info("✅ AIAnalysisService инициализирован")
    
    
    async def generate_summary_only(self, title: str, content: str) -> str:
        """
        Генерирует только краткое саммари новости.
        
        Args:
            title: Заголовок новости
            content: Содержание новости
            
        Returns:
            str: Краткое саммари
        """
        try:
            # Используем ProxyAPI для генерации саммари
            if self.use_proxy and self.client:
                logger.info("🚀 Используем ProxyAPI для генерации саммари")
                
                # Создаем промпт для саммари
                summary_prompt = f"""
                Создай краткое саммари следующей новости из мира ИИ согласно требованиям ZeBrains:

                ЗАГОЛОВОК: {title}
                СОДЕРЖАНИЕ: {content}

                ТРЕБОВАНИЯ К САММАРИ:
                - Объем: 1-3 предложения (50-100 слов)
                - Формат: краткое описание сути новости без лишних деталей
                - Только ключевые факты

                ФОРМАТ ОТВЕТА:
                Только готовое саммари в 1-3 предложения (50-100 слов) без дополнительных пояснений.
                """
                
                # Вызываем OpenAI API через прокси
                try:
                    response = self.client.chat.completions.create(
                        model=config.ai.model,
                        messages=[{"role": "user", "content": summary_prompt}]
                    )
                    
                    summary = response.choices[0].message.content.strip()
                    logger.info(f"✅ Саммари сгенерировано: {len(summary)} символов")
                    return summary
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка ProxyAPI при генерации саммари: {e}")
                    logger.error(f"❌ Тип ошибки: {type(e).__name__}")
                    logger.error(f"❌ Детали: {str(e)}")
                    logger.warning("⚠️ Переходим к базовому саммари")
                    return f"Краткое саммари: {title}"
            else:
                logger.warning("⚠️ ProxyAPI недоступен, используем базовое саммари")
                return f"Краткое саммари: {title}"
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации саммари: {e}")
            return f"Краткое саммари: {title}"
    
    def analyze_text(self, prompt: str) -> str:
        """
        Анализирует текст с помощью AI для генерации контента.
        
        Args:
            prompt: Промпт для AI
            
        Returns:
            Сгенерированный текст
        """
        try:
            # Используем ProxyAPI для генерации текста
            if hasattr(self, 'use_proxy') and self.use_proxy and self.client:
                try:
                    # Синхронный вызов к ProxyAPI
                    response = self.client.chat.completions.create(
                        model=config.ai.model,
                        messages=[
                            {"role": "system", "content": "Ты - профессиональный SMM-менеджер, создающий качественный контент для дайджестов новостей об ИИ."},
                            {"role": "user", "content": prompt}
                        ]
                    )
                    
                    result = response.choices[0].message.content.strip()
                    logger.info("✅ AI текст сгенерирован успешно")
                    return result
                    
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка AI запроса: {e}, используем fallback")
                    return self._generate_fallback_text(prompt)
            
            # Fallback - возвращаем простой ответ
            logger.warning("⚠️ AI недоступен, используем fallback для генерации текста")
            return self._generate_fallback_text(prompt)
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа текста: {e}")
            return self._generate_fallback_text(prompt)
    
    def _generate_fallback_text(self, prompt: str) -> str:
        """
        Генерирует fallback текст когда AI недоступен.
        
        Args:
            prompt: Исходный промпт
            
        Returns:
            Fallback текст
        """
        if "введение" in prompt.lower():
            return "Привет! Я Алекс, цифровой SMM-менеджер ZeBrains. На этой неделе разбираем новости ИИ вместе со Степаном Игониным, руководителем отдела ИИ."
        elif "заключение" in prompt.lower():
            return "На этом у меня всё! Какая новость вас удивила больше всего? Делитесь в комментариях! 🔥"
        elif "интегрируй комментарий" in prompt.lower():
            # Извлекаем имя эксперта из промпта
            if "Степан Игонин" in prompt:
                return "Это открывает новые возможности для бизнеса и может кардинально изменить подход к автоматизации процессов"
            else:
                return "Это важная новость, которая может повлиять на развитие отрасли."
        else:
            return "Текст обработан успешно."

    def get_proxy_status(self) -> dict:
        """Возвращает статус ProxyAPI сервиса."""
        return {
            "service": "AIAnalysisService",
            "proxy_available": self.use_proxy,
            "proxy_url": self.proxy_url,
            "proxy_api_key_set": bool(self.proxy_api_key),
            "client_initialized": self.client is not None,
            "message": "ProxyAPI работает как полноценный AI сервис" if self.use_proxy else "ProxyAPI не настроен - добавьте PROXY_API_URL и PROXY_API_KEY в .env"
        }

    async def analyze_news_relevance(self, title: str, content: str) -> Optional[int]:
        """
        Анализирует релевантность новости для ИИ-дайджеста..
        
        Args:
            title: Заголовок новости
            content: Содержание новости
            
        Returns:
            int: Оценка релевантности от 0 до 10, или None при ошибке
        """
        if not self.client or not self.use_proxy:
            logger.warning("⚠️ AI анализ недоступен, используем fallback по ключевым словам")
            return self._fallback_relevance_check(title, content)
        
        try:
            # Промпт для оценки релевантности
            relevance_prompt = f"""
            Ты - эксперт по анализу новостей в области искусственного интеллекта, машинного обучения и технологий.

            Проанализируй новость и определи, насколько она релевантна для ИИ-дайджеста.

            ЗАГОЛОВОК: {title}
            СОДЕРЖАНИЕ: {content}

            КРИТЕРИИ РЕЛЕВАНТНОСТИ:
            1. Прямо связана с ИИ/ML/NLP/робототехникой
            2. Касается технологических инноваций в ИИ
            3. Влияет на развитие ИИ-индустрии
            4. Интересна для специалистов по ИИ

            ОЦЕНИ ПО ШКАЛЕ 0-10, где:
            - 0-3: НЕ релевантна (новости о политике, спорте, развлечениях)
            - 4-6: Слабо релевантна (общие технологии, упоминание ИИ вскользь)
            - 7-10: Высоко релевантна (прямо про ИИ, ML, AI-инструменты)

            ВЕРНИ ТОЛЬКО ЧИСЛО ОТ 0 ДО 10.
            """

            logger.info(f"🤖 Анализируем релевантность новости: {title[:50]}...")
            
            # Используем существующую логику AI запросов
            try:
                # Пробуем разные модели
                models_to_try = [config.ai.model, "gpt-4", "gpt-3.5-turbo"]
                response = None
                
                for model in models_to_try:
                    try:
                        logger.info(f"🤖 Пробуем модель {model} для анализа релевантности")
                        response = self.client.chat.completions.create(
                            model=model,
                            messages=[{"role": "user", "content": relevance_prompt}]
                        )
                        logger.info(f"✅ Успешно использована модель: {model}")
                        break
                    except Exception as model_error:
                        logger.warning(f"⚠️ Модель {model} не работает: {model_error}")
                        continue
                
                if not response:
                    raise Exception("Ни одна из моделей не работает")
                
                # Извлекаем ответ
                ai_response = response.choices[0].message.content.strip()
                
                try:
                    # Извлекаем число из ответа
                    relevance_score = int(ai_response)
                    if 0 <= relevance_score <= 10:
                        logger.info(f"✅ Релевантность новости: {relevance_score}/10")
                        return relevance_score
                    else:
                        logger.warning(f"⚠️ Некорректная оценка релевантности: {relevance_score}")
                        return self._fallback_relevance_check(title, content)
                except ValueError:
                    logger.warning(f"⚠️ Не удалось извлечь число из ответа AI: {ai_response}")
                    return self._fallback_relevance_check(title, content)
                    
            except Exception as e:
                logger.error(f"❌ Ошибка AI запроса: {e}")
                return self._fallback_relevance_check(title, content)
                
        except Exception as e:
            logger.error(f"❌ Ошибка AI анализа релевантности: {e}")
            return self._fallback_relevance_check(title, content)
    
    def _fallback_relevance_check(self, title: str, content: str) -> int:
        """
        Fallback проверка релевантности по ключевым словам.
        
        Args:
            title: Заголовок новости
            content: Содержание новости
            
        Returns:
            int: Оценка релевантности от 0 до 10
        """
        # Ключевые слова для ИИ-новостей
        ai_keywords = [
            'искусственный интеллект', 'AI', 'машинное обучение', 'ML', 
            'нейросеть', 'GPT', 'ChatGPT', 'OpenAI', 'Google AI', 'Microsoft AI',
            'робот', 'автоматизация', 'алгоритм', 'дата-сайенс', 'big data',
            'deep learning', 'компьютерное зрение', 'NLP', 'обработка языка',
            'нейронная сеть', 'машинное обучение', 'искусственный интеллект',
            'AI модель', 'AI инструмент', 'AI платформа', 'AI сервис'
        ]
        
        # Объединяем заголовок и содержание для поиска
        full_text = f"{title} {content}".lower()
        
        # Подсчитываем количество найденных ключевых слов
        found_keywords = sum(1 for keyword in ai_keywords if keyword.lower() in full_text)
        
        # Оцениваем релевантность на основе количества ключевых слов
        if found_keywords >= 3:
            relevance_score = 8  # Высоко релевантна
        elif found_keywords >= 2:
            relevance_score = 6  # Средне релевантна
        elif found_keywords >= 1:
            relevance_score = 4  # Слабо релевантна
        else:
            relevance_score = 2  # Не релевантна
        
        logger.info(f"🔍 Fallback оценка релевантности: {relevance_score}/10 (найдено ключевых слов: {found_keywords})")
        return relevance_score
