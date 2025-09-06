# 🚀 План миграции от Mock к реальной системе

## 📋 **Текущее состояние (Mock/Заглушки)**

### ✅ **Что работает с заглушками:**
- Telegram-бот с полным интерфейсом
- Все команды и обработчики
- Архитектура и структура кода
- Тестирование всех компонентов

### ❌ **Что нужно заменить на реальное:**

#### **1. База данных**
- **Сейчас:** MockDatabaseService с тестовыми данными
- **Нужно:** Реальная PostgreSQL/MySQL база данных
- **Что делать:** 
  - Создать схему базы данных
  - Настроить подключение к реальной БД
  - Заменить MockDatabaseService на RealDatabaseService

#### **2. OpenAI сервис**
- **Сейчас:** MockOpenAIService с фиксированными ответами
- **Нужно:** Реальное подключение к OpenAI API
- **Что делать:**
  - Получить API ключ OpenAI
  - Настроить реальные запросы к GPT
  - Обработать ошибки и лимиты API

#### **3. Эксперты**
- **Сейчас:** Тестовые эксперты в Mock данных
- **Нужно:** Реальные люди-эксперты
- **Что делать:**
  - Добавить реальных экспертов в систему
  - Настроить уведомления для экспертов
  - Создать процесс назначения заданий

#### **4. Новости**
- **Сейчас:** Статичные тестовые новости
- **Нужно:** Автоматический парсинг из Telegram-каналов
- **Что делать:**
  - Создать NewsParserService
  - Настроить мониторинг каналов
  - Реализовать детекцию дубликатов

## 🎯 **Пошаговый план миграции**

### **Этап 1: Реальная база данных (1-2 дня)**

#### **Шаг 1.1: Настройка PostgreSQL**
```bash
# Установка PostgreSQL
brew install postgresql
brew services start postgresql

# Создание базы данных
createdb ai_news_assistant
```

#### **Шаг 1.2: Создание схемы БД**
```python
# Создать файл database_schema.sql
CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    telegram_id VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE news (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    source_id INTEGER REFERENCES sources(id),
    status VARCHAR(50) DEFAULT 'pending',
    url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    curator_id INTEGER,
    curated_at TIMESTAMP
);

# ... остальные таблицы
```

#### **Шаг 1.3: Реальный DatabaseService**
```python
# Создать RealDatabaseService
class RealDatabaseService:
    def __init__(self):
        self.engine = create_engine('postgresql://user:pass@localhost/ai_news_assistant')
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def get_session(self):
        return self.SessionLocal()
```

### **Этап 2: Реальный OpenAI (1 день)**

#### **Шаг 2.1: Настройка API ключа**
```python
# В .env файле
OPENAI_API_KEY=your_real_openai_api_key

# В коде
import openai
openai.api_key = os.getenv('OPENAI_API_KEY')
```

#### **Шаг 2.2: Реальный OpenAIService**
```python
class RealOpenAIService:
    def generate_summary(self, text: str) -> str:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Создай краткое саммари: {text}"}]
        )
        return response.choices[0].message.content
```

### **Этап 3: Система уведомлений (2-3 дня)**

#### **Шаг 3.1: NotificationService**
```python
class NotificationService:
    def notify_expert(self, expert_id: int, news_id: int):
        # Отправка уведомления эксперту в Telegram
        pass
    
    def send_reminder(self, expert_id: int):
        # Напоминание о невыполненных заданиях
        pass
```

#### **Шаг 3.2: Автоматическое назначение**
```python
class AutoAssignmentService:
    def auto_assign_experts(self):
        # Автоматическое назначение экспертов к новым новостям
        pass
```

### **Этап 4: Парсинг новостей (3-4 дня)**

#### **Шаг 4.1: NewsParserService**
```python
class NewsParserService:
    def parse_telegram_channels(self):
        # Парсинг новостей из Telegram-каналов
        pass
    
    def detect_duplicates(self, news_content: str):
        # Детекция дубликатов
        pass
```

#### **Шаг 4.2: Планировщик задач**
```python
# Использовать APScheduler для автоматического парсинга
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
scheduler.add_job(parse_news, 'interval', hours=1)
scheduler.start()
```

## 🔄 **Гибридный подход (рекомендуемый)**

### **Фаза 1: Частичная замена (1 неделя)**
- Заменить базу данных на реальную
- Оставить Mock для OpenAI (для экономии)
- Добавить реальных экспертов
- Протестировать полный цикл

### **Фаза 2: Полная замена (1 неделя)**
- Заменить OpenAI на реальный API
- Добавить парсинг новостей
- Настроить автоматизацию

### **Фаза 3: Продакшен (1 неделя)**
- Настройка мониторинга
- Обработка ошибок
- Документация

## 🛠 **Практические шаги для начала**

### **1. Создать конфигурацию для переключения**
```python
# В config.py
class Config:
    USE_MOCK_DATABASE = os.getenv('USE_MOCK_DATABASE', 'true').lower() == 'true'
    USE_MOCK_OPENAI = os.getenv('USE_MOCK_OPENAI', 'true').lower() == 'true'
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://...')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
```

### **2. Factory для выбора сервисов**
```python
class ServiceFactory:
    @staticmethod
    def create_database_service():
        if Config.USE_MOCK_DATABASE:
            return MockDatabaseService()
        else:
            return RealDatabaseService()
    
    @staticmethod
    def create_openai_service():
        if Config.USE_MOCK_OPENAI:
            return MockOpenAIService()
        else:
            return RealOpenAIService()
```

### **3. Постепенная миграция**
```bash
# Начать с базы данных
export USE_MOCK_DATABASE=false
export DATABASE_URL=postgresql://user:pass@localhost/ai_news_assistant

# Затем OpenAI
export USE_MOCK_OPENAI=false
export OPENAI_API_KEY=your_key
```

## 📊 **Метрики готовности**

### **Готовность к продакшену:**
- [ ] Реальная база данных настроена и работает
- [ ] OpenAI API интегрирован и протестирован
- [ ] Система уведомлений работает
- [ ] Парсинг новостей автоматизирован
- [ ] Мониторинг и логирование настроены
- [ ] Обработка ошибок реализована
- [ ] Документация обновлена

## 🎯 **Рекомендации**

### **Начать с:**
1. **База данных** - это основа системы
2. **Реальные эксперты** - чтобы протестировать полный цикл
3. **OpenAI API** - для реальных саммари

### **Оставить на потом:**
1. **Автоматический парсинг** - можно добавлять новости вручную
2. **Сложную автоматизацию** - сначала убедиться, что базовая функциональность работает

## 💡 **Вывод**

Сейчас у нас есть **отличный прототип** с правильной архитектурой. Заглушки позволяют:
- Тестировать интерфейс и логику
- Демонстрировать функциональность
- Разрабатывать без зависимости от внешних сервисов

**Следующий шаг:** Выбрать, с чего начать миграцию - база данных или реальные эксперты? 