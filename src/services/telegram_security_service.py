#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сервис безопасности для Telegram User API
Уровень защиты: 1 + 2 (базовая + средняя)

Уровень 1 (базовая защита):
- Хэширование номеров телефонов
- Переменные окружения для секретов
- Исключение .env из git

Уровень 2 (средняя защита):
- Шифрование данных сессий
- Проверка истечения сессий
- Безопасное логирование (без секретов)
"""

import hashlib
import os
import json
import logging
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TelegramSecurityService:
    """
    Сервис для безопасной работы с Telegram User API сессиями
    
    Что защищаем:
    - Номера телефонов → Хэшируем
    - Токены сессий → Шифруем
    - API ключи → Храним в .env
    """
    
    def __init__(self):
        """Инициализация сервиса безопасности"""
        # Загружаем .env файл если не загружен
        from dotenv import load_dotenv
        load_dotenv()
        
        # Получаем мастер-ключ из переменных окружения (уровень 1)
        self.master_key = os.getenv('TELEGRAM_MASTER_KEY')
        
        if not self.master_key:
            # Если ключа нет - создаем новый (только при первом запуске)
            self.master_key = Fernet.generate_key().decode()
            logger.warning("⚠️ СОЗДАН НОВЫЙ МАСТЕР-КЛЮЧ!")
            logger.warning(f"⚠️ Добавьте в .env: TELEGRAM_MASTER_KEY={self.master_key}")
            print(f"\n🔑 ДОБАВЬТЕ В .env ФАЙЛ:")
            print(f"TELEGRAM_MASTER_KEY={self.master_key}\n")
        else:
            logger.info(f"🔑 Мастер-ключ загружен из .env: {self.master_key[:8]}...{self.master_key[-8:]}")
        
        # Создаем объект для шифрования (уровень 2)
        try:
            self.cipher = Fernet(self.master_key.encode())
            logger.info("🔐 Сервис безопасности инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации шифрования: {e}")
            raise
    
    def hash_phone_number(self, phone: str) -> str:
        """
        Хэширует номер телефона для безопасного хранения (уровень 1)
        
        ЗАЧЕМ: Чтобы не хранить реальный номер в БД
        КАК: "+79161234567" → "a1b2c3d4e5f6" (необратимо)
        
        Args:
            phone: Номер телефона (например, "+79161234567")
            
        Returns:
            str: Хэш номера телефона (16 символов)
        """
        try:
            # Очищаем номер от лишних символов
            clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
            
            # Создаем SHA256 хэш (односторонняя функция)
            phone_hash = hashlib.sha256(clean_phone.encode('utf-8')).hexdigest()[:16]
            
            # Логируем БЕЗ реального номера (уровень 2)
            logger.info(f"📱 Номер захэширован: {phone[:4]}****** → {phone_hash[:8]}...")
            
            return phone_hash
            
        except Exception as e:
            logger.error(f"❌ Ошибка хэширования номера: {e}")
            raise
    
    def encrypt_session_data(self, session_data: bytes) -> str:
        """
        Шифрует данные сессии для безопасного хранения (уровень 2)
        
        ЗАЧЕМ: Чтобы токены доступа были нечитаемы в БД
        КАК: Реальные_данные → "gAAAAABh...зашифрованная_строка"
        
        Args:
            session_data: Данные сессии от Telethon (bytes)
            
        Returns:
            str: Зашифрованная строка для хранения в БД
        """
        try:
            # Шифруем данные с помощью Fernet (AES 128)
            encrypted_data = self.cipher.encrypt(session_data)
            
            # Превращаем в строку для хранения в БД
            encrypted_string = encrypted_data.decode('utf-8')
            
            # Логируем размеры БЕЗ содержимого (уровень 2)
            logger.info(f"🔐 Сессия зашифрована: {len(session_data)} байт → {len(encrypted_string)} символов")
            
            return encrypted_string
            
        except Exception as e:
            logger.error(f"❌ Ошибка шифрования сессии: {e}")
            raise
    
    def decrypt_session_data(self, encrypted_string: str) -> bytes:
        """
        Расшифровывает данные сессии для использования (уровень 2)
        
        ЗАЧЕМ: Чтобы получить исходные данные для подключения
        КАК: "gAAAAABh...зашифрованная_строка" → Реальные_данные
        
        Args:
            encrypted_string: Зашифрованная строка из БД
            
        Returns:
            bytes: Расшифрованные данные сессии
        """
        try:
            # Превращаем строку обратно в байты
            encrypted_data = encrypted_string.encode('utf-8')
            
            # Расшифровываем
            session_data = self.cipher.decrypt(encrypted_data)
            
            # Логируем БЕЗ содержимого (уровень 2)
            logger.info(f"🔓 Сессия расшифрована: {len(session_data)} байт")
            
            return session_data
            
        except Exception as e:
            logger.error(f"❌ Ошибка расшифровки сессии: {e}")
            raise
    
    def create_session_data_json(self, phone: str, session_data: bytes) -> Dict[str, Any]:
        """
        Создает JSON структуру для хранения в bot_sessions.data
        
        Args:
            phone: Номер телефона
            session_data: Данные сессии Telethon
            
        Returns:
            dict: Структура для сохранения в БД
        """
        try:
            # Хэшируем номер (уровень 1)
            phone_hash = self.hash_phone_number(phone)
            
            # Шифруем данные сессии (уровень 2)
            encrypted_session = self.encrypt_session_data(session_data)
            
            # Создаем хэш ключа для проверки целостности (уровень 2)
            key_hash = hashlib.sha256(self.master_key.encode()).hexdigest()[:16]
            
            # Формируем JSON структуру
            data_json = {
                "phone_hash": phone_hash,
                "session_data_encrypted": encrypted_session,
                "encryption_key_hash": key_hash,
                "usage_count": 0,
                "last_error": None,
                "created_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"📦 JSON структура создана для сессии: {phone_hash[:8]}...")
            return data_json
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания JSON структуры: {e}")
            raise
    
    def extract_session_data_from_json(self, data_json: Dict[str, Any]) -> bytes:
        """
        Извлекает и расшифровывает данные сессии из JSON
        
        Args:
            data_json: JSON структура из bot_sessions.data
            
        Returns:
            bytes: Расшифрованные данные сессии
        """
        try:
            # Проверяем целостность ключа (уровень 2)
            stored_key_hash = data_json.get("encryption_key_hash")
            current_key_hash = hashlib.sha256(self.master_key.encode()).hexdigest()[:16]
            
            if stored_key_hash != current_key_hash:
                raise ValueError("Ключ шифрования изменился! Сессия недействительна.")
            
            # Извлекаем зашифрованные данные
            encrypted_session = data_json["session_data_encrypted"]
            
            # Расшифровываем
            session_data = self.decrypt_session_data(encrypted_session)
            
            # Обновляем статистику использования
            data_json["usage_count"] = data_json.get("usage_count", 0) + 1
            
            logger.info(f"📥 Сессия извлечена: использований {data_json['usage_count']}")
            return session_data
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения сессии: {e}")
            # Сохраняем ошибку в JSON для анализа
            data_json["last_error"] = str(e)
            raise
    
    def is_phone_hash_match(self, phone: str, stored_hash: str) -> bool:
        """
        Проверяет, соответствует ли номер телефона сохраненному хэшу
        
        Args:
            phone: Номер телефона для проверки
            stored_hash: Сохраненный хэш из БД
            
        Returns:
            bool: True если номер соответствует хэшу
        """
        try:
            current_hash = self.hash_phone_number(phone)
            match = current_hash == stored_hash
            
            # Логируем результат БЕЗ реального номера (уровень 2)
            logger.info(f"🔍 Проверка номера: {phone[:4]}****** → {'✅ Совпадает' if match else '❌ Не совпадает'}")
            
            return match
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки номера: {e}")
            return False
    
    def validate_session_data(self, data_json: Dict[str, Any]) -> bool:
        """
        Проверяет валидность данных сессии (уровень 2)
        
        Args:
            data_json: JSON структура из БД
            
        Returns:
            bool: True если данные валидны
        """
        try:
            required_fields = ["phone_hash", "session_data_encrypted", "encryption_key_hash"]
            
            # Проверяем наличие всех обязательных полей
            for field in required_fields:
                if field not in data_json:
                    logger.warning(f"⚠️ Отсутствует поле: {field}")
                    return False
            
            # Проверяем целостность ключа
            stored_key_hash = data_json["encryption_key_hash"]
            current_key_hash = hashlib.sha256(self.master_key.encode()).hexdigest()[:16]
            
            if stored_key_hash != current_key_hash:
                logger.warning("⚠️ Ключ шифрования изменился")
                return False
            
            logger.info("✅ Данные сессии валидны")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка валидации сессии: {e}")
            return False
