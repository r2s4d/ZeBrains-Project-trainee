# 🚀 Развертывание AI News Assistant Bot

## Системные требования

### Минимальные требования
- **OS**: Ubuntu 20.04+ / CentOS 8+ / macOS 10.15+
- **Python**: 3.8+
- **RAM**: 4 GB
- **CPU**: 2 ядра
- **Storage**: 20 GB свободного места
- **Network**: Стабильное интернет-соединение

### Рекомендуемые требования
- **OS**: Ubuntu 22.04 LTS
- **Python**: 3.9+
- **RAM**: 8 GB
- **CPU**: 4 ядра
- **Storage**: 50 GB SSD
- **Network**: Выделенный IP, 100+ Mbps

## 📋 Предварительная подготовка

### 1. Создание Telegram бота

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте команду `/newbot`
3. Введите имя бота: `AI News Assistant`
4. Введите username: `your_ai_news_bot`
5. Сохраните полученный токен

### 2. Создание канала

1. Создайте новый канал в Telegram
2. Добавьте бота как администратора
3. Дайте права на отправку сообщений
4. Сохраните ID канала (начинается с @)

### 3. Настройка ProxyAPI

1. Зарегистрируйтесь на [ProxyAPI](https://proxyapi.ru)
2. Получите API ключ
3. Сохраните URL API (обычно `https://openai.api.proxyapi.ru/v1`)

### 4. Настройка PostgreSQL

1. Установите PostgreSQL 12+
2. Создайте базу данных:
```sql
CREATE DATABASE ai_news_db;
CREATE USER ai_news_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE ai_news_db TO ai_news_user;
```

## 🛠️ Установка

### 1. Клонирование репозитория

```bash
git clone https://github.com/your-username/ai_news_assistant.git
cd ai_news_assistant
```

### 2. Создание виртуального окружения

```bash
# Создание виртуального окружения
python3 -m venv venv

# Активация (Linux/macOS)
source venv/bin/activate

# Активация (Windows)
venv\Scripts\activate
```

### 3. Установка зависимостей

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=8195833718:AAGbqnbZz7NrbOWN5ic5k7oxGMUTntgHE6s
TELEGRAM_CHANNEL_ID=@egor4ik1234
CURATORS_CHAT_ID=-1002983482030

# Database Configuration
DATABASE_URL=postgresql://ai_news_user:secure_password@localhost:5432/ai_news_db

# AI Service Configuration
PROXY_API_URL=https://openai.api.proxyapi.ru/v1
PROXY_API_KEY=sk-your-proxy-api-key-here

# Optional: Logging Level
LOG_LEVEL=INFO
```

### 5. Инициализация базы данных

```bash
python -c "from src.models.database import init_db; init_db()"
```

### 6. Добавление источников новостей

```bash
python -c "
from src.services.postgresql_database_service import PostgreSQLDatabaseService
from src.models.database import Source

db = PostgreSQLDatabaseService()
with db.get_session() as session:
    # Добавляем источники новостей
    sources = [
        Source(name='AI News', url='https://t.me/ai_news', is_active=True),
        Source(name='ML News', url='https://t.me/ml_news', is_active=True),
        Source(name='Tech News', url='https://t.me/tech_news', is_active=True)
    ]
    for source in sources:
        session.add(source)
    session.commit()
    print('Источники новостей добавлены!')
"
```

### 7. Добавление экспертов

```bash
python -c "
from src.services.postgresql_database_service import PostgreSQLDatabaseService
from src.models.database import Expert

db = PostgreSQLDatabaseService()
with db.get_session() as session:
    # Добавляем экспертов
    experts = [
        Expert(name='Доктор Алексеев', specialization='ИИ и машинное обучение', is_active=True),
        Expert(name='Профессор Иванов', specialization='Нейронные сети', is_active=True),
        Expert(name='Доктор Петров', specialization='Компьютерное зрение', is_active=True)
    ]
    for expert in experts:
        session.add(expert)
    session.commit()
    print('Эксперты добавлены!')
"
```

## 🚀 Запуск

### 1. Ручной запуск

```bash
python run_bot.py
```

### 2. Запуск в фоне (Linux/macOS)

```bash
nohup python run_bot.py > bot.log 2>&1 &
```

### 3. Запуск с systemd (Linux)

Создайте файл `/etc/systemd/system/ai-news-bot.service`:

```ini
[Unit]
Description=AI News Assistant Bot
After=network.target postgresql.service

[Service]
Type=simple
User=ai_news
WorkingDirectory=/opt/ai_news_assistant
Environment=PATH=/opt/ai_news_assistant/venv/bin
ExecStart=/opt/ai_news_assistant/venv/bin/python run_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Запуск:
```bash
sudo systemctl enable ai-news-bot
sudo systemctl start ai-news-bot
sudo systemctl status ai-news-bot
```

## 🔧 Конфигурация

### 1. Настройка планировщика

Планировщик автоматически запускается при старте бота. Для ручной настройки:

```bash
# Запуск планировщика
python -c "
from src.bot.bot import AINewsBot
bot = AINewsBot()
bot.scheduler_service.start()
"
```

### 2. Настройка логирования

Создайте файл `logging.conf`:

```ini
[loggers]
keys=root,bot

[handlers]
keys=consoleHandler,fileHandler

[formatters]
keys=simpleFormatter

[logger_root]
level=INFO
handlers=consoleHandler,fileHandler

[logger_bot]
level=DEBUG
handlers=consoleHandler,fileHandler
qualname=bot.bot
propagate=0

[handler_consoleHandler]
class=StreamHandler
level=INFO
formatter=simpleFormatter
args=(sys.stdout,)

[handler_fileHandler]
class=FileHandler
level=DEBUG
formatter=simpleFormatter
args=('bot.log',)

[formatter_simpleFormatter]
format=%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

### 3. Настройка мониторинга

Для мониторинга состояния бота:

```bash
# Проверка статуса
ps aux | grep python | grep run_bot

# Проверка логов
tail -f bot.log

# Проверка базы данных
psql -U ai_news_user -d ai_news_db -c "SELECT COUNT(*) FROM news;"
```

## 🔒 Безопасность

### 1. Защита токенов

```bash
# Установка правильных прав на .env
chmod 600 .env
chown ai_news:ai_news .env
```

### 2. Firewall

```bash
# Открытие только необходимых портов
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 5432/tcp  # PostgreSQL (только для локальных подключений)
sudo ufw enable
```

### 3. SSL для PostgreSQL

```bash
# В postgresql.conf
ssl = on
ssl_cert_file = 'server.crt'
ssl_key_file = 'server.key'
```

## 📊 Мониторинг и обслуживание

### 1. Логирование

```bash
# Ротация логов
sudo logrotate -f /etc/logrotate.d/ai-news-bot
```

### 2. Резервное копирование

```bash
# Бэкап базы данных
pg_dump -U ai_news_user ai_news_db > backup_$(date +%Y%m%d).sql

# Бэкап конфигурации
tar -czf config_backup_$(date +%Y%m%d).tar.gz .env src/config/
```

### 3. Обновление

```bash
# Остановка бота
sudo systemctl stop ai-news-bot

# Обновление кода
git pull origin main

# Установка новых зависимостей
pip install -r requirements.txt

# Запуск бота
sudo systemctl start ai-news-bot
```

## 🐛 Устранение неполадок

### 1. Бот не запускается

```bash
# Проверка логов
tail -f bot.log

# Проверка зависимостей
pip list | grep -E "(telegram|sqlalchemy|psycopg2)"

# Проверка переменных окружения
python -c "import os; print(os.getenv('TELEGRAM_BOT_TOKEN'))"
```

### 2. Ошибки базы данных

```bash
# Проверка подключения
psql -U ai_news_user -d ai_news_db -c "SELECT 1;"

# Проверка таблиц
psql -U ai_news_user -d ai_news_db -c "\dt"
```

### 3. Ошибки AI сервиса

```bash
# Проверка ProxyAPI
curl -H "Authorization: Bearer $PROXY_API_KEY" $PROXY_API_URL/models

# Проверка в коде
python -c "
from src.services.ai_analysis_service import AIAnalysisService
ai = AIAnalysisService()
print(ai.get_proxy_status())
"
```

## 📈 Масштабирование

### 1. Горизонтальное масштабирование

- Запуск нескольких экземпляров бота
- Использование Redis для координации
- Балансировка нагрузки

### 2. Вертикальное масштабирование

- Увеличение RAM и CPU
- Оптимизация запросов к БД
- Кэширование часто используемых данных

---

*Инструкция по развертыванию обеспечивает надежную и безопасную работу AI News Assistant Bot в продакшене.*
