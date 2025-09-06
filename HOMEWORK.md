# 🏠 Домашнее задание

## 📅 Дата: 31 июля 2025 г.

### 🎯 Задание 1: Добавить новые функции в DatabaseService

Добавьте следующие функции в файл `src/services/database_service.py`:

#### 1. Функция поиска новостей по заголовку
```python
def search_news_by_title(self, title: str) -> List[News]:
    """
    Ищет новости по части заголовка (регистронезависимый поиск)
    
    Args:
        title (str): Часть заголовка для поиска
        
    Returns:
        List[News]: Список найденных новостей
    """
    pass
```

#### 2. Функция получения новостей за определенную дату
```python
def get_news_by_date(self, date: datetime.date) -> List[News]:
    """
    Получает все новости, созданные в указанную дату
    
    Args:
        date (datetime.date): Дата для поиска
        
    Returns:
        List[News]: Список новостей за указанную дату
    """
    pass
```

#### 3. Функция получения новостей по статусу с лимитом
```python
def get_news_by_status_with_limit(self, status: str, limit: int = 10) -> List[News]:
    """
    Получает новости по статусу с ограничением количества
    
    Args:
        status (str): Статус новостей
        limit (int): Максимальное количество новостей
        
    Returns:
        List[News]: Список новостей
    """
    pass
```

### 🎯 Задание 2: Создать тесты для новых функций

Создайте файл `test_new_functions.py` и напишите тесты для новых функций:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для новых функций DatabaseService
"""

import os
import sys
from datetime import datetime, date

# Добавляем папку src в путь для импорта модулей
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.database_service import db_service

def test_new_functions():
    """Тестирует новые функции DatabaseService."""
    
    print("🧪 Тестирование новых функций DatabaseService...")
    
    # Тест 1: Поиск новостей по заголовку
    print("\n📰 Тест 1: Поиск новостей по заголовку")
    # Добавьте тестовые новости и проверьте поиск
    
    # Тест 2: Получение новостей за дату
    print("\n📅 Тест 2: Получение новостей за дату")
    # Добавьте тестовые новости и проверьте фильтрацию по дате
    
    # Тест 3: Получение новостей с лимитом
    print("\n📊 Тест 3: Получение новостей с лимитом")
    # Добавьте тестовые новости и проверьте лимит

if __name__ == "__main__":
    test_new_functions()
```

### 🎯 Задание 3: Создать файл .env

1. Скопируйте файл `env_example.txt` как `.env`
2. Заполните настройки базы данных (уже готовы)
3. Остальные настройки оставьте как есть (заполните позже)

### 📚 Что нужно изучить:

1. **SQL LIKE** — для поиска по части строки
2. **SQL DATE** — для работы с датами
3. **SQL LIMIT** — для ограничения количества результатов
4. **Python datetime** — для работы с датами и временем

### 🔍 Полезные ссылки:

- [SQLAlchemy Query API](https://docs.sqlalchemy.org/en/14/orm/query.html)
- [SQL LIKE operator](https://www.w3schools.com/sql/sql_like.asp)
- [Python datetime](https://docs.python.org/3/library/datetime.html)

### ✅ Критерии оценки:

- [ ] Функции работают корректно
- [ ] Обработка ошибок реализована
- [ ] Тесты проходят успешно
- [ ] Код написан читаемо и с комментариями

---

**Срок выполнения:** До следующей сессии

**Вопросы:** Задавайте в чате, если что-то непонятно! 