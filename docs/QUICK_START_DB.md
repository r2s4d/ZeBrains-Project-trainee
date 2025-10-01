# 🚀 Быстрый старт с PostgreSQL - Практический пример

## Шаг 1: Запустить PostgreSQL

```bash
# Запустить PostgreSQL
brew services start postgresql@15

# Проверить статус
brew services list | grep postgres
# Должно быть: postgresql@15 started
```

## Шаг 2: Подключиться к БД

Откройте Terminal и введите:

```bash
psql -h localhost -U postgres -d ai_news_db
```

**Что вы увидите:**
```
Password for user postgres: [введите пароль]
psql (15.x)
Type "help" for help.

ai_news_db=# 
```

✅ Если видите `ai_news_db=#` - вы подключены!

## Шаг 3: Первые команды

Скопируйте и вставьте эти команды **по очереди**:

### 1. Посмотреть все таблицы
```sql
\dt
```

**Вы увидите:**
```
                List of relations
 Schema |        Name        | Type  |  Owner   
--------+--------------------+-------+----------
 public | digest_sessions    | table | postgres  ← Наша таблица!
 public | news               | table | postgres
 ...
```

### 2. Посмотреть структуру таблицы digest_sessions
```sql
\d digest_sessions
```

**Вы увидите все поля (колонки) таблицы.**

### 3. Посмотреть все данные в таблице
```sql
SELECT * FROM digest_sessions;
```

Если таблица пустая, увидите:
```
(0 rows)
```

Если есть данные, увидите таблицу с записями.

### 4. Посмотреть только активные сессии
```sql
SELECT * FROM digest_sessions WHERE is_active = true;
```

### 5. Подсчитать количество записей
```sql
SELECT COUNT(*) FROM digest_sessions;
```

Вы увидите:
```
 count 
-------
     0
(1 row)
```

### 6. Выйти из psql
```sql
\q
```

Вы вернетесь в обычный Terminal.

---

## 🎨 Альтернатива: Использование DBeaver (графический интерфейс)

### Установка
```bash
brew install --cask dbeaver-community
```

### Подключение

1. Откройте DBeaver
2. Нажмите "Database" → "New Database Connection"
3. Выберите "PostgreSQL"
4. Заполните:
   - **Host:** `localhost`
   - **Port:** `5432`
   - **Database:** `ai_news_db`
   - **Username:** `postgres`
   - **Password:** [ваш пароль из `.env`]
5. Нажмите "Test Connection"
6. Нажмите "Finish"

### Использование

1. В левой панели найдите:
   ```
   PostgreSQL → ai_news_db → Schemas → public → Tables
   ```

2. Кликните правой кнопкой на `digest_sessions`

3. Выберите "View Data" → Откроется таблица!

4. Для SQL-запросов:
   - Нажмите `Cmd + ]` (New SQL Script)
   - Напишите: `SELECT * FROM digest_sessions;`
   - Нажмите `Cmd + Enter` (выполнить)

---

## 📊 Практический пример: Проверка после запуска бота

### 1. Запустите бота
```bash
python run_bot.py
```

### 2. Создайте дайджест
Отправьте в чат кураторов: `/morning_digest`

### 3. Проверьте в БД (в другом окне Terminal)
```bash
psql -h localhost -U postgres -d ai_news_db
```

```sql
-- Посмотреть все активные сессии
SELECT * FROM digest_sessions WHERE is_active = true;

-- Вы должны увидеть новую запись!
```

### 4. Одобрите дайджест в Telegram

### 5. Снова проверьте БД
```sql
-- Сессия должна стать неактивной
SELECT * FROM digest_sessions ORDER BY created_at DESC LIMIT 1;
-- is_active должен быть false
```

---

## 💡 Полезные советы

### Совет 1: Сохраните часто используемые команды

Создайте файл `~/my_queries.sql`:
```sql
-- Активные сессии
SELECT * FROM digest_sessions WHERE is_active = true;

-- Последние 10 сессий
SELECT * FROM digest_sessions ORDER BY created_at DESC LIMIT 10;

-- Статистика
SELECT 
    is_active,
    COUNT(*) as количество
FROM digest_sessions
GROUP BY is_active;
```

Запуск:
```bash
psql -h localhost -U postgres -d ai_news_db -f ~/my_queries.sql
```

### Совет 2: Alias для быстрого доступа

Добавьте в `~/.zshrc`:
```bash
alias db='psql -h localhost -U postgres -d ai_news_db'
```

Теперь просто пишите:
```bash
db
```

### Совет 3: Используйте историю команд

В psql нажмите **стрелку вверх ↑** для повтора предыдущих команд.

---

## 🆘 Что делать, если не работает?

### Проблема: "connection refused"
```bash
# Запустить PostgreSQL
brew services start postgresql@15
```

### Проблема: "password authentication failed"
```bash
# Проверьте пароль в .env
cat .env | grep DATABASE_PASSWORD
```

### Проблема: "database does not exist"
```bash
# Создайте базу
psql -U postgres -c "CREATE DATABASE ai_news_db;"
```

---

## 📚 Дальнейшее обучение

1. **Полное руководство:** [DATABASE_BEGINNER_GUIDE.md](DATABASE_BEGINNER_GUIDE.md)
2. **Шпаргалка команд:** [SQL_CHEATSHEET.md](SQL_CHEATSHEET.md)
3. **Миграция сессий:** [../MIGRATION_DIGEST_SESSIONS_GUIDE.md](../MIGRATION_DIGEST_SESSIONS_GUIDE.md)

---

## 🎯 Резюме: 3 способа работы с БД

### Способ 1: Терминал (для профи)
```bash
psql -h localhost -U postgres -d ai_news_db
```
**Плюсы:** Быстро, доступно везде  
**Минусы:** Нужно знать команды

### Способ 2: DBeaver (рекомендуется для начинающих!)
```bash
brew install --cask dbeaver-community
```
**Плюсы:** Визуальный интерфейс, легко учиться  
**Минусы:** Нужно устанавливать

### Способ 3: Python-скрипт (для автоматизации)
```python
from sqlalchemy import create_engine
engine = create_engine('postgresql://postgres:password@localhost/ai_news_db')
# Используйте в коде
```
**Плюсы:** Автоматизация  
**Минусы:** Нужно программировать

---

**Начните с DBeaver - это самый простой способ для изучения!** 🚀

**Версия:** 1.0  
**Создано:** 2025-10-01

