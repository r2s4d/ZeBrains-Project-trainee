# 🎨 Пошаговая инструкция по настройке DBeaver

## ✅ DBeaver успешно установлен!

Приложение запущено. Следуйте этим шагам для подключения к базе данных.

---

## 📋 Шаг 1: Создать новое подключение

После запуска DBeaver вы увидите главное окно.

**Действия:**
1. Нажмите на кнопку "New Database Connection" (иконка с вилкой и знаком +)
   
   **ИЛИ**
   
2. В меню: **Database** → **New Database Connection**

   **ИЛИ**
   
3. Нажмите `Cmd + N` (быстрая клавиша)

---

## 📋 Шаг 2: Выбрать PostgreSQL

В открывшемся окне "Connect to a database":

1. В списке баз данных найдите и выберите **PostgreSQL**
   - Иконка синего слона 🐘
   - Обычно в верхней части списка

2. Нажмите кнопку **Next** внизу окна

---

## 📋 Шаг 3: Заполнить параметры подключения

Вы увидите форму с полями подключения.

### Вкладка "Main" (основная):

Заполните следующие поля:

```
┌─────────────────────────────────────────────┐
│ Host:         localhost                     │
│ Port:         5432                          │
│ Database:     ai_news_db                    │
│ Username:     postgres                      │
│ Password:     [ваш пароль]                  │
│                                             │
│ [✓] Save password                           │
└─────────────────────────────────────────────┘
```

**Где взять пароль?**

Откройте в другом окне Terminal и выполните:
```bash
cat .env | grep DATABASE_PASSWORD
```

Или посмотрите в файле `.env` в корне проекта.

**Важно:**
- ✅ Поставьте галочку **"Save password"**, чтобы не вводить каждый раз
- ✅ Убедитесь, что `Database` = `ai_news_db` (именно так, без опечаток)

---

## 📋 Шаг 4: Проверить подключение

Перед сохранением проверьте, что всё работает:

1. Нажмите кнопку **"Test Connection"** внизу окна

2. Вы увидите одно из двух:

### ✅ Успешное подключение:
```
Connected
PostgreSQL 12.x - 15.x
Database: ai_news_db
```

**Отлично!** Нажмите **"OK"**, затем **"Finish"**.

### ❌ Ошибка подключения:

**Возможные проблемы и решения:**

#### Проблема 1: "Connection refused"
```
FATAL: connection refused
```

**Решение:** PostgreSQL не запущен
```bash
# Запустить PostgreSQL
brew services start postgresql@15

# Проверить статус
brew services list | grep postgres
```

#### Проблема 2: "Password authentication failed"
```
FATAL: password authentication failed for user "postgres"
```

**Решение:** Неверный пароль
- Проверьте пароль в файле `.env`
- Убедитесь, что копируете без пробелов в начале/конце

#### Проблема 3: "Database does not exist"
```
FATAL: database "ai_news_db" does not exist
```

**Решение:** База данных не создана
```bash
# Создать базу данных
psql -U postgres -c "CREATE DATABASE ai_news_db;"
```

#### Проблема 4: "Driver not found"

**Решение:** DBeaver попросит скачать драйвер
- Нажмите **"Download"** в диалоговом окне
- Дождитесь загрузки (займет 10-30 секунд)
- Нажмите **"Test Connection"** еще раз

---

## 📋 Шаг 5: Открыть базу данных

После успешного подключения вы увидите в левой панели:

```
📁 PostgreSQL - ai_news_db
   └─ 📁 Databases
       └─ 📦 ai_news_db
           └─ 📁 Schemas
               └─ 📁 public
                   └─ 📁 Tables
                       ├─ 📊 bot_sessions
                       ├─ 📊 digest_sessions  ← Наша таблица!
                       ├─ 📊 news
                       ├─ 📊 sources
                       └─ ...
```

---

## 📋 Шаг 6: Посмотреть данные в таблице

### Способ 1: Визуально (самый простой)

1. В левой панели раскройте дерево до **Tables**
2. Найдите таблицу **digest_sessions**
3. **Кликните правой кнопкой мыши** на `digest_sessions`
4. Выберите **"View Data"** → **"View First 100 Rows"**

**Готово!** Вы увидите таблицу с данными! 🎉

### Способ 2: SQL-запрос

1. Нажмите `Cmd + ]` или кнопку **"SQL Editor"** → **"New SQL Script"**
2. В открывшемся редакторе напишите:
   ```sql
   SELECT * FROM digest_sessions;
   ```
3. Нажмите `Cmd + Enter` или кнопку **"Execute"** (▶️)

**Готово!** Вы увидите результат запроса! 🎉

---

## 🎨 Полезные возможности DBeaver

### 1. Автодополнение SQL

Когда пишете SQL-запрос:
- Начните печатать `SEL...` → появятся подсказки
- Нажмите `Tab` для автодополнения

### 2. Форматирование SQL

Если запрос выглядит неаккуратно:
- Нажмите `Cmd + Shift + F` (форматировать код)

### 3. Экспорт данных

Чтобы сохранить данные в Excel или CSV:
1. Выполните запрос
2. В результатах нажмите правой кнопкой
3. Выберите **"Export Data"**
4. Выберите формат (CSV, Excel, JSON)

### 4. История запросов

Все ваши запросы сохраняются:
- Откройте **"SQL Editor"** → **"SQL History"**
- Или нажмите `Cmd + Shift + H`

### 5. Множественные вкладки

Можете открыть несколько SQL-редакторов одновременно:
- `Cmd + ]` для новой вкладки

---

## 🎯 Первые запросы для проверки

После подключения попробуйте эти запросы:

### 1. Посмотреть все активные сессии
```sql
SELECT * FROM digest_sessions WHERE is_active = true;
```

### 2. Подсчитать количество сессий
```sql
SELECT COUNT(*) FROM digest_sessions;
```

### 3. Последние 10 сессий
```sql
SELECT 
    id,
    chat_id,
    news_count,
    is_active,
    created_at
FROM digest_sessions 
ORDER BY created_at DESC 
LIMIT 10;
```

### 4. Статистика
```sql
SELECT 
    is_active,
    COUNT(*) as количество
FROM digest_sessions
GROUP BY is_active;
```

---

## 🆘 Если DBeaver не запускается на macOS 11

Если DBeaver показывает ошибку при запуске, используйте **альтернативные инструменты**:

### Альтернатива 1: Терминал (всегда работает)

```bash
# Подключиться к БД
psql -h localhost -U postgres -d ai_news_db

# Посмотреть таблицы
\dt

# Посмотреть данные
SELECT * FROM digest_sessions;

# Выйти
\q
```

### Альтернатива 2: Postico (легкий, для macOS)

```bash
# Установить
brew install --cask postico

# Запустить
open -a Postico
```

Postico легче, чем DBeaver, и может лучше работать на macOS 11.

### Альтернатива 3: pgAdmin 4 (официальный)

```bash
# Установить
brew install --cask pgadmin4

# Запустить
open -a pgAdmin\ 4
```

---

## 💡 Советы по работе с DBeaver

### Совет 1: Закрепите в Dock

Для быстрого доступа:
1. Правой кнопкой на иконку DBeaver в Dock
2. **Options** → **Keep in Dock**

### Совет 2: Настройте горячие клавиши

**Window** → **Preferences** → **User Interface** → **Keys**

Полезные:
- `Cmd + Enter` - выполнить запрос
- `Cmd + ]` - новый SQL-редактор
- `Cmd + Shift + F` - форматировать SQL

### Совет 3: Включите темную тему

Если любите темную тему:
- **Window** → **Preferences** → **General** → **Appearance**
- Выберите **Dark** theme

### Совет 4: Сохраняйте часто используемые запросы

1. Напишите запрос в SQL Editor
2. **File** → **Save As**
3. Сохраните с понятным именем, например `check_active_sessions.sql`

---

## 🎉 Готово!

Теперь вы можете:
- ✅ Подключаться к базе данных визуально
- ✅ Просматривать данные в таблицах
- ✅ Выполнять SQL-запросы
- ✅ Отслеживать работу бота в реальном времени

---

## 📚 Дальнейшее обучение

1. **Полное руководство:** [DATABASE_BEGINNER_GUIDE.md](DATABASE_BEGINNER_GUIDE.md)
2. **Шпаргалка SQL:** [SQL_CHEATSHEET.md](SQL_CHEATSHEET.md)
3. **Быстрый старт:** [QUICK_START_DB.md](QUICK_START_DB.md)

---

## 🆘 Нужна помощь?

Если возникли проблемы:
1. Проверьте, что PostgreSQL запущен: `brew services list | grep postgres`
2. Проверьте пароль в `.env`: `cat .env | grep DATABASE`
3. Попробуйте подключиться через терминал: `psql -h localhost -U postgres -d ai_news_db`

---

**Успехов в изучении баз данных!** 🚀

**Версия:** 1.0  
**Дата:** 2025-10-01  
**Для:** macOS 11+ и DBeaver Community

