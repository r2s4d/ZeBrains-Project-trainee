#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MessageSplitter - универсальная утилита для разделения длинных сообщений.

Используется в сервисах для разбиения дайджестов, списков новостей и других 
длинных текстов на части, не превышающие лимиты Telegram.
"""

import logging
from typing import List, Dict, Optional, Callable

from src.config.settings import config

logger = logging.getLogger(__name__)


class MessageSplitter:
    """
    Универсальный класс для разделения длинных сообщений на части.
    
    Используется для:
    - Разделения утренних дайджестов по новостям
    - Разделения списков новостей для экспертов
    - Разделения финальных дайджестов по блокам
    """
    
    @staticmethod
    def split_by_items(
        items: List,
        header: str,
        item_formatter: Callable[[int, any], str],
        max_length: Optional[int] = None,
        include_metadata: bool = True
    ) -> List[Dict]:
        """
        Разбивает список элементов (новостей) на части с сохранением метаданных.
        
        Используется в:
        - MorningDigestService._split_message_by_news
        - ExpertInteractionService._split_news_list_for_expert
        
        Args:
            items: Список элементов для разбиения
            header: Заголовок, который будет в начале каждой части
            item_formatter: Функция форматирования элемента (index, item) -> str
            max_length: Максимальная длина части (default: из конфига)
            include_metadata: Включать ли метаданные (news_indices, buttons)
            
        Returns:
            List[Dict]: Список частей с структурой:
                - text: Текст части
                - news_indices: Индексы новостей в части (если include_metadata=True)
                - buttons: Индексы кнопок (если include_metadata=True)
        
        Example:
            >>> items = [news1, news2, news3]
            >>> def formatter(i, news):
            ...     return f"{i+1}. {news.summary}\\n"
            >>> parts = MessageSplitter.split_by_items(
            ...     items, "📰 Новости:\\n\\n", formatter
            ... )
        """
        if not items:
            return []
        
        if max_length is None:
            max_length = config.message.max_news_list_length
        
        parts = []
        current_part = header
        current_indices = []
        
        for i, item in enumerate(items):
            # Форматируем элемент
            item_text = item_formatter(i, item)
            
            # Проверяем, не превысит ли добавление элемента лимит
            if len(current_part + item_text) > max_length and current_part != header:
                # Сохраняем текущую часть
                part_data = {'text': current_part}
                if include_metadata:
                    part_data['news_indices'] = current_indices
                    part_data['buttons'] = current_indices.copy()
                parts.append(part_data)
                
                # Начинаем новую часть
                current_part = header + item_text
                current_indices = [i]
            else:
                # Добавляем элемент к текущей части
                current_part += item_text
                current_indices.append(i)
        
        # Добавляем последнюю часть
        if current_part and current_part != header:
            part_data = {'text': current_part}
            if include_metadata:
                part_data['news_indices'] = current_indices
                part_data['buttons'] = current_indices.copy()
            parts.append(part_data)
        
        logger.info(f"📝 Разделено на {len(parts)} частей (макс. длина: {max_length})")
        return parts
    
    @staticmethod
    def split_by_blocks(
        text: str,
        max_length: Optional[int] = None,
        block_separator: str = '\n\n',
        sentence_separator: str = '. '
    ) -> List[str]:
        """
        Разбивает длинный текст на части по логическим блокам.
        
        Используется в:
        - FinalDigestFormatterService.split_digest_message
        
        Алгоритм:
        1. Разбивает текст по блокам (обычно двойные переносы строк)
        2. Если блок слишком длинный, разбивает по предложениям
        3. Собирает части, не превышающие max_length
        
        Args:
            text: Текст для разбиения
            max_length: Максимальная длина части (default: из конфига)
            block_separator: Разделитель блоков (default: '\\n\\n')
            sentence_separator: Разделитель предложений (default: '. ')
            
        Returns:
            List[str]: Список частей текста
        
        Example:
            >>> text = "Блок 1\\n\\nБлок 2\\n\\nОчень длинный блок..."
            >>> parts = MessageSplitter.split_by_blocks(text)
        """
        if max_length is None:
            max_length = config.message.max_digest_length
        
        # Если текст помещается целиком
        if len(text) <= max_length:
            return [text]
        
        parts = []
        current_part = ""
        
        # Разбиваем по блокам
        blocks = text.split(block_separator)
        
        for block in blocks:
            # Пропускаем пустые блоки
            if not block.strip():
                continue
            
            # Если блок помещается в текущую часть
            if len(current_part + block + block_separator) <= max_length:
                current_part += block + block_separator
            else:
                # Сохраняем текущую часть
                if current_part:
                    parts.append(current_part.strip())
                
                # Если блок сам по себе слишком длинный
                if len(block) > max_length:
                    # Разбиваем по предложениям
                    sub_parts = MessageSplitter._split_long_block(
                        block, max_length, sentence_separator
                    )
                    # Добавляем все части кроме последней
                    parts.extend(sub_parts[:-1])
                    # Последняя часть становится началом следующей
                    current_part = sub_parts[-1] + block_separator
                else:
                    # Блок становится началом новой части
                    current_part = block + block_separator
        
        # Добавляем последнюю часть
        if current_part:
            parts.append(current_part.strip())
        
        logger.info(f"📝 Текст разделен на {len(parts)} частей (макс. длина: {max_length})")
        return parts
    
    @staticmethod
    def _split_long_block(
        block: str,
        max_length: int,
        sentence_separator: str = '. '
    ) -> List[str]:
        """
        Внутренний метод для разбиения слишком длинного блока по предложениям.
        
        Args:
            block: Блок текста
            max_length: Максимальная длина
            sentence_separator: Разделитель предложений
            
        Returns:
            List[str]: Список частей блока
        """
        parts = []
        sentences = block.split(sentence_separator)
        current_part = ""
        
        for sentence in sentences:
            # Если предложение само по себе длиннее лимита, обрезаем
            if len(sentence) > max_length:
                logger.warning(f"⚠️ Предложение длиннее лимита ({len(sentence)} > {max_length}), обрезаем")
                sentence = sentence[:max_length - 3] + "..."
            
            # Проверяем, поместится ли предложение
            if len(current_part + sentence + sentence_separator) <= max_length:
                current_part += sentence + sentence_separator
            else:
                # Сохраняем текущую часть
                if current_part:
                    parts.append(current_part.strip())
                # Начинаем новую часть
                current_part = sentence + sentence_separator
        
        # Добавляем последнюю часть
        if current_part:
            parts.append(current_part.strip())
        
        return parts if parts else [""]

