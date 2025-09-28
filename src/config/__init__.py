#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль конфигурации AI News Assistant.
"""

from .settings import config, AppConfig, DatabaseConfig, TelegramConfig, AIConfig, SecurityConfig, TimeoutConfig, MessageConfig, ExpertConfig, DuplicateDetectionConfig

__all__ = [
    'config',
    'AppConfig', 
    'DatabaseConfig',
    'TelegramConfig',
    'AIConfig',
    'SecurityConfig',
    'TimeoutConfig',
    'MessageConfig',
    'ExpertConfig',
    'DuplicateDetectionConfig'
]
