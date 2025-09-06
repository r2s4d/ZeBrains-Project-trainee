"""
Конфигурация для Telegram API и парсинга каналов.
"""

import os
from typing import List, Dict
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

class TelegramConfig:
    """Конфигурация для работы с Telegram API."""
    
    # Telegram API ключи (получить на https://my.telegram.org)
    API_ID = os.getenv('TELEGRAM_API_ID')
    API_HASH = os.getenv('TELEGRAM_API_HASH')
    
    # Настройки парсинга
    PARSING_INTERVAL_HOURS = 2  # Парсинг каждые 2 часа
    MAX_MESSAGES_PER_CHANNEL = 50  # Максимум сообщений для парсинга за раз
    NIGHT_MODE_INTERVAL_HOURS = 4  # Ночной режим (21:00 - 9:00)
    
    # Список каналов для парсинга (согласно функциональным требованиям)
    CHANNELS = [
        {
            'username': 'ai_ins',
            'name': 'AI Insights',
            'description': 'Новости и аналитика в области ИИ',
            'active': True
        },
        {
            'username': 'ai_machinelearning_big_data',
            'name': 'Machine Learning News',
            'description': 'Новости машинного обучения и больших данных',
            'active': True
        },
        {
            'username': 'ppprompt',
            'name': 'Prompt Engineering',
            'description': 'Инженерия промптов и работа с ИИ',
            'active': True
        },
        {
            'username': 'AGI_Boardroom',
            'name': 'AGI Boardroom',
            'description': 'Обсуждения AGI и будущего ИИ',
            'active': True
        },
        {
            'username': 'sergiobulaev',
            'name': 'Сергей Булаев AI',
            'description': 'Экспертные мнения по ИИ',
            'active': True
        }
    ]
    
    # Расписание парсинга (рабочие часы)
    PARSING_SCHEDULE = {
        'active_hours': {
            'start': 9,  # 9:00
            'end': 21,   # 21:00
            'interval': 2  # каждые 2 часа
        },
        'night_hours': {
            'start': 21,  # 21:00
            'end': 9,     # 9:00
            'interval': 4  # каждые 4 часа
        }
    }
    
    # Настройки логирования
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    @classmethod
    def validate_config(cls) -> bool:
        """Проверяет корректность конфигурации."""
        if not cls.API_ID:
            print("❌ TELEGRAM_API_ID не найден в .env файле")
            return False
        
        if not cls.API_HASH:
            print("❌ TELEGRAM_API_HASH не найден в .env файле")
            return False
        
        try:
            int(cls.API_ID)
        except ValueError:
            print("❌ TELEGRAM_API_ID должен быть числом")
            return False
        
        if len(cls.API_HASH) != 32:
            print("❌ TELEGRAM_API_HASH должен быть строкой из 32 символов")
            return False
        
        print("✅ Конфигурация Telegram API корректна")
        return True
    
    @classmethod
    def get_active_channels(cls) -> List[Dict]:
        """Возвращает список активных каналов."""
        return [channel for channel in cls.CHANNELS if channel['active']]
    
    @classmethod
    def get_channel_by_username(cls, username: str) -> Dict:
        """Находит канал по username."""
        for channel in cls.CHANNELS:
            if channel['username'] == username:
                return channel
        return None

# Тестирование конфигурации
if __name__ == "__main__":
    print("🔧 Проверка конфигурации Telegram API...")
    if TelegramConfig.validate_config():
        print(f"📱 Найдено {len(TelegramConfig.get_active_channels())} активных каналов")
        for channel in TelegramConfig.get_active_channels():
            print(f"  • @{channel['username']} - {channel['name']}")
    else:
        print("❌ Конфигурация некорректна")
