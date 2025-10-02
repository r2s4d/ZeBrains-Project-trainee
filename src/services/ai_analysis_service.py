#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI анализ новостей с использованием OpenAI API.
Обновленная версия: объединенный промпт для саммари и анализа.
"""

import asyncio
import logging
import os
import hashlib
from datetime import datetime
from typing import Optional
from dataclasses import dataclass
from openai import OpenAI
from src.config import config
from src.services.sqlite_cache_service import cache, get_cache_key
from src.utils.timeout_utils import with_timeout, AI_REQUEST_TIMEOUT
from src.utils.retry_utils import ai_retry, ai_circuit_breaker

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
    
    
    @ai_retry
    @ai_circuit_breaker
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
            # Создаем ключ кэша для саммари
            content_hash = hashlib.md5(f"{title}_{content}".encode()).hexdigest()
            cache_key = get_cache_key("ai_summary", content_hash)
            
            # Проверяем кэш
            cached_summary = cache.get(cache_key)
            if cached_summary:
                logger.info(f"🎯 Саммари из кэша: {len(cached_summary)} символов")
                return cached_summary
            
            # Используем ProxyAPI для генерации саммари
            if self.use_proxy and self.client:
                logger.info("🚀 Используем ProxyAPI для генерации саммари")
                
                # Создаем промпт для саммари (БЕЗ заголовка)
                summary_prompt = f"""
                Создай краткое саммари для новости об ИИ (БЕЗ заголовка):

                СОДЕРЖАНИЕ: {content}

                ТРЕБОВАНИЯ:
                - Объем: 1-3 предложения (50-100 слов)
                - Краткое описание сути без лишних деталей
                - Только ключевые факты
                - НЕ включай заголовок в саммари
                - БЕЗ звездочек ** - использовать только HTML теги <b></b> для выделения

                ФОРМАТ ОТВЕТА (только саммари):
                Краткое саммари в 1-3 предложения с ключевыми фактами.
                """
                
                # Вызываем OpenAI API через прокси с таймаутом
                try:
                    loop = asyncio.get_event_loop()
                    response = await with_timeout(
                        loop.run_in_executor(
                            None,
                            lambda: self.client.chat.completions.create(
                                model=config.ai.model,
                                messages=[{"role": "user", "content": summary_prompt}]
                            )
                        ),
                        timeout_seconds=AI_REQUEST_TIMEOUT,
                        operation_name="генерация саммари",
                        fallback_value=None
                    )
                    
                    summary = response.choices[0].message.content.strip()
                    
                    # Очищаем от звездочек и улучшаем форматирование
                    clean_summary = self._clean_markdown_artifacts(summary)
                    
                    logger.info(f"✅ Саммари сгенерировано: {len(clean_summary)} символов")
                    
                    # Сохраняем в кэш на 24 часа
                    cache.set(cache_key, clean_summary, expire_seconds=86400)
                    logger.debug(f"💾 Саммари сохранено в кэш: {cache_key}")
                    
                    return clean_summary
                    
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
    
    async def analyze_text(self, prompt: str) -> str:
        """
        Анализирует текст с помощью AI для генерации контента.
        
        Args:
            prompt: Промпт для AI
            
        Returns:
            Сгенерированный текст
        """
        try:
            # Создаем ключ кэша для анализа текста
            prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
            cache_key = get_cache_key("ai_text", prompt_hash)
            
            # Проверяем кэш
            cached_text = cache.get(cache_key)
            if cached_text:
                logger.info(f"🎯 AI текст из кэша: {len(cached_text)} символов")
                return cached_text
            
            # Используем ProxyAPI для генерации текста
            if hasattr(self, 'use_proxy') and self.use_proxy and self.client:
                try:
                    # Синхронный вызов к ProxyAPI с таймаутом через run_in_executor
                    loop = asyncio.get_event_loop()
                    response = await with_timeout(
                        loop.run_in_executor(
                            None,
                            lambda: self.client.chat.completions.create(
                                model=config.ai.model,
                                messages=[
                                    {"role": "system", "content": "Ты - профессиональный SMM-менеджер, создающий качественный контент для дайджестов новостей об ИИ."},
                                    {"role": "user", "content": prompt}
                                ]
                            )
                        ),
                        timeout_seconds=AI_REQUEST_TIMEOUT,
                        operation_name="генерация текста",
                        fallback_value=None
                    )
                    
                    result = response.choices[0].message.content.strip()
                    logger.info("✅ AI текст сгенерирован успешно")
                    
                    # Сохраняем в кэш на 24 часа
                    cache.set(cache_key, result, expire_seconds=86400)
                    logger.debug(f"💾 AI текст сохранен в кэш: {cache_key}")
                    
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

    @ai_retry
    @ai_circuit_breaker
    async def analyze_news_relevance(self, title: str, content: str) -> Optional[int]:
        """
        Анализирует релевантность новости для ИИ-дайджеста.
        
        Args:
            title: Заголовок новости
            content: Содержание новости
            
        Returns:
            int: Оценка релевантности от 0 до 10, или None при ошибке
        """
        # Создаем ключ кэша для анализа релевантности
        content_hash = hashlib.md5(f"{title}_{content}".encode()).hexdigest()
        cache_key = get_cache_key("ai_relevance", content_hash)
        
        # Проверяем кэш
        cached_relevance = cache.get(cache_key)
        if cached_relevance is not None:
            logger.info(f"🎯 Релевантность из кэша: {cached_relevance}/10")
            return cached_relevance
        
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
                        loop = asyncio.get_event_loop()
                        response = await with_timeout(
                            loop.run_in_executor(
                                None,
                                lambda: self.client.chat.completions.create(
                                    model=model,
                                    messages=[{"role": "user", "content": relevance_prompt}]
                                )
                            ),
                            timeout_seconds=AI_REQUEST_TIMEOUT,
                            operation_name=f"анализ релевантности ({model})",
                            fallback_value=None
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
                        
                        # Сохраняем в кэш на 24 часа
                        cache.set(cache_key, relevance_score, expire_seconds=86400)
                        logger.debug(f"💾 Релевантность сохранена в кэш: {cache_key}")
                        
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
    
    def _clean_markdown_artifacts(self, text: str) -> str:
        """
        Очищает текст от звездочек и других markdown артефактов.
        
        Args:
            text: Исходный текст
            
        Returns:
            Очищенный текст с HTML тегами
        """
        try:
            # Убираем двойные звездочки ** и заменяем на HTML теги
            import re
            
            # Заменяем **текст** на <b>текст</b>
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            
            # Убираем одинарные звездочки *
            text = re.sub(r'\*([^*]+)\*', r'<i>\1</i>', text)
            
            # Убираем оставшиеся звездочки
            text = text.replace('*', '')
            
            # Убираем лишние пробелы
            text = re.sub(r'\s+', ' ', text).strip()
            
            logger.debug(f"🧹 Текст очищен от markdown артефактов")
            return text
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки текста: {e}")
            return text
    
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
