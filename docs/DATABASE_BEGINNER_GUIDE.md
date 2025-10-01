# 🎓 PostgreSQL для начинающих - Полное руководство

## 📖 Содержание
1. [Что такое база данных](#что-такое-база-данных)
2. [Как подключиться к БД](#как-подключиться-к-бд)
3. [Основные команды PostgreSQL](#основные-команды-postgresql)
4. [SQL-запросы для вашего проекта](#sql-запросы-для-проекта)
5. [GUI-инструменты (графические программы)](#gui-инструменты)
6. [Практические примеры](#практические-примеры)
7. [Частые ошибки и решения](#частые-ошибки)

---

## 🗄️ Что такое база данных?

### Простыми словами:

**База данных (БД)** - это организованное хранилище информации, похожее на Excel-таблицу, но намного мощнее и быстрее.

**PostgreSQL** - это программа (система управления БД), которая:
- Хранит данные в таблицах (как листы в Excel)
- Позволяет быстро искать и изменять данные
- Защищает данные от потерь
- Работает намного быстрее обычных файлов

### В вашем проекте AI News Assistant:

```
База данных: ai_news_assistant
│
├── Таблица: digest_sessions     ← сессии дайджестов (наша новая система!)
│   ├── id                       ← уникальный номер сессии
│   ├── chat_id                  ← ID чата Telegram
│   ├── message_ids              ← ID сообщений (JSON)
│   ├── news_count               ← количество новостей
│   ├── is_active                ← активна ли сессия
│   ├── created_at               ← когда создана
│   └── updated_at               ← когда обновлена
│
├── Таблица: news                ← новости
├── Таблица: bot_sessions        ← другие сессии бота
├── Таблица: sources             ← источники новостей
└── Таблица: experts             ← эксперты
```

---

## 🔌 Как подключиться к БД

### Способ 1: Через терминал (командная строка)

#### Шаг 1: Открыть терминал на macOS

1. Нажмите `Cmd + Пробел` (откроется Spotlight)
2. Напишите "Terminal"
3. Нажмите Enter

#### Шаг 2: Подключиться к PostgreSQL

Скопируйте и вставьте эту команду:

```bash
psql -h localhost -U postgres -d ai_news_db
```

**Разбор команды по словам:**

| Часть | Что означает | Объяснение |
|-------|--------------|------------|
| `psql` | Программа PostgreSQL Client | Это "клиент" для общения с БД |
| `-h localhost` | Host = localhost | Адрес сервера БД. `localhost` = ваш компьютер |
| `-U postgres` | User = postgres | Имя пользователя БД. `postgres` - это администратор |
| `-d ai_news_db` | Database = ai_news_db | Название вашей базы данных |

**Что произойдет:**

```
Password for user postgres: 
```

Введите пароль от PostgreSQL (который вы указывали в `.env` файле) и нажмите Enter.

⚠️ **Важно:** Пароль не отображается при вводе - это нормально для безопасности!

**Успешное подключение выглядит так:**

```
psql (12.10)
Type "help" for help.

ai_news_db=# 
```

Приглашение `ai_news_db=#` означает, что вы **внутри базы данных** и готовы вводить команды! 🎉

#### Шаг 3: Первая проверка

Проверьте, что вы подключены к правильной БД:

```sql
SELECT current_database();
```

**Вывод:**
```
 current_database 
------------------
 ai_news_db
(1 row)
```

Отлично! Вы внутри базы `ai_news_db`.

---

## 📝 Основные команды PostgreSQL

### Два типа команд:

#### 🔹 Тип 1: Метакоманды (начинаются с `\`)
Это команды **для управления** psql, а не для работы с данными.

#### 🔹 Тип 2: SQL-запросы (заканчиваются на `;`)
Это команды **для работы с данными** в таблицах.

---

### 🎯 Метакоманды для навигации

```sql
-- Показать все таблицы в БД
\dt

-- Показать структуру конкретной таблицы
\d digest_sessions

-- Показать список всех баз данных
\l

-- Показать пользователей БД
\du

-- Помощь по всем командам
\?

-- Помощь по SQL-командам
\h

-- Выход из psql
\q
```

#### Примеры использования:

**1. Посмотреть все таблицы:**

```sql
ai_news_db=# \dt
```

**Вывод:**
```
                List of relations
 Schema |        Name        | Type  |  Owner   
--------+--------------------+-------+----------
 public | bot_sessions       | table | postgres
 public | comments           | table | postgres
 public | curators           | table | postgres
 public | digest_sessions    | table | postgres  ← Наша новая таблица!
 public | experts            | table | postgres
 public | news               | table | postgres
 public | sources            | table | postgres
(7 rows)
```

**2. Посмотреть структуру таблицы digest_sessions:**

```sql
ai_news_db=# \d digest_sessions
```

**Вывод:**
```
                                     Table "public.digest_sessions"
    Column     |           Type              | Nullable |                  Default                   
---------------+-----------------------------+----------+--------------------------------------------
 id            | integer                     | not null | nextval('digest_sessions_id_seq')
 chat_id       | character varying           | not null | 
 message_ids   | text                        | not null | 
 news_count    | integer                     | not null | 
 created_at    | timestamp without time zone |          | now()
 updated_at    | timestamp without time zone |          | now()
 is_active     | boolean                     |          | true
```

**Что означают колонки:**
- `id` - уникальный номер записи (1, 2, 3...)
- `chat_id` - ID чата Telegram (строка, например "-1002983482030")
- `message_ids` - список ID сообщений в JSON формате
- `news_count` - количество новостей (целое число)
- `is_active` - активна ли сессия (true/false)
- `created_at` - дата и время создания
- `updated_at` - дата и время последнего обновления

---

## 🔍 SQL-запросы для работы с данными

### Базовая структура SQL-запроса:

```sql
SELECT [что выбрать] FROM [откуда] WHERE [условие];
```

### 4 главные команды SQL (CRUD):

| Команда | Что делает | Аналогия |
|---------|------------|----------|
| `SELECT` | Читает данные | Как "открыть и посмотреть таблицу" |
| `INSERT` | Добавляет данные | Как "добавить новую строку" |
| `UPDATE` | Изменяет данные | Как "отредактировать ячейку" |
| `DELETE` | Удаляет данные | Как "удалить строку" |

---

## 🎯 SQL-запросы для вашего проекта

### 1️⃣ Посмотреть ВСЕ сессии дайджестов

```sql
SELECT * FROM digest_sessions;
```

**Разбор команды:**
- `SELECT *` - выбрать ВСЕ колонки (звездочка `*` = всё)
- `FROM digest_sessions` - из таблицы digest_sessions
- `;` - **обязательная** точка с запятой в конце команды

**Пример вывода:**
```
 id |     chat_id      |      message_ids       | news_count | is_active |      created_at         |      updated_at      
----+------------------+------------------------+------------+-----------+-------------------------+----------------------
  1 | -1002983482030   | [237, 238, 239, 240]   |         21 | t         | 2025-10-01 09:00:00.123 | 2025-10-01 09:00:00
  2 | -1002983482030   | [250, 251, 252]        |         15 | f         | 2025-10-01 10:30:00.456 | 2025-10-01 11:00:00
(2 rows)
```

**Объяснение вывода:**
- В БД есть 2 записи (2 rows)
- Первая сессия (id=1): активная (`is_active = t`, где t = true)
- Вторая сессия (id=2): неактивная (`is_active = f`, где f = false)
- В первой сессии 21 новость, во второй 15

### 2️⃣ Посмотреть только АКТИВНЫЕ сессии

```sql
SELECT * FROM digest_sessions WHERE is_active = true;
```

**Разбор команды:**
- `WHERE is_active = true` - добавили условие "только активные"
- `WHERE` в SQL означает "где выполняется условие"

**Пример вывода:**
```
 id |     chat_id      |      message_ids       | news_count | is_active |      created_at      
----+------------------+------------------------+------------+-----------+----------------------
  1 | -1002983482030   | [237, 238, 239, 240]   |         21 | t         | 2025-10-01 09:00:00
(1 row)
```

Показывается только одна запись - та, где `is_active = true`.

### 3️⃣ Посмотреть последние 5 сессий (самые новые)

```sql
SELECT * FROM digest_sessions 
ORDER BY created_at DESC 
LIMIT 5;
```

**Разбор команды:**
- `ORDER BY created_at DESC` - отсортировать по дате создания
  - `ORDER BY` = "сортировать по"
  - `DESC` = descending (по убыванию, от новых к старым)
  - Если нужно наоборот: `ASC` = ascending (по возрастанию, от старых к новым)
- `LIMIT 5` - показать только 5 записей

### 4️⃣ Посмотреть только нужные колонки

```sql
SELECT chat_id, news_count, is_active, created_at 
FROM digest_sessions 
WHERE is_active = true;
```

**Разбор команды:**
- Вместо `*` (всё) перечислили конкретные колонки через запятую
- Вывод будет компактнее и понятнее

**Пример вывода:**
```
     chat_id      | news_count | is_active |      created_at      
------------------+------------+-----------+----------------------
 -1002983482030   |         21 | t         | 2025-10-01 09:00:00
(1 row)
```

### 5️⃣ Посмотреть сессию для конкретного чата

```sql
SELECT * FROM digest_sessions 
WHERE chat_id = '-1002983482030';
```

**Разбор команды:**
- `WHERE chat_id = '-1002983482030'` - условие "где chat_id равен этому значению"
- Обратите внимание на **одинарные кавычки** `'...'` для текстовых значений

### 6️⃣ Подсчитать количество сессий

```sql
-- Всего сессий
SELECT COUNT(*) FROM digest_sessions;

-- Активных сессий
SELECT COUNT(*) FROM digest_sessions WHERE is_active = true;

-- Неактивных сессий
SELECT COUNT(*) FROM digest_sessions WHERE is_active = false;
```

**Разбор команды:**
- `COUNT(*)` - подсчитать количество строк
- `--` в начале строки = комментарий (не выполняется)

**Пример вывода:**
```
 count 
-------
     5
(1 row)
```

### 7️⃣ Статистика по сессиям (группировка)

```sql
SELECT 
    is_active,
    COUNT(*) as количество,
    MAX(created_at) as последнее_обновление
FROM digest_sessions
GROUP BY is_active;
```

**Разбор команды:**
- `COUNT(*) as количество` - подсчитать и назвать колонку "количество"
- `MAX(created_at)` - найти максимальное (самое новое) значение даты
- `GROUP BY is_active` - сгруппировать по статусу (true/false)
- `as` = "назвать как" (задать псевдоним колонке)

**Пример вывода:**
```
 is_active | количество | последнее_обновление 
-----------+------------+----------------------
 t         |          3 | 2025-10-01 14:00:00
 f         |          7 | 2025-10-01 12:00:00
(2 rows)
```

**Объяснение:**
- 3 активных сессии (is_active = t)
- 7 неактивных сессий (is_active = f)
- Последняя активная сессия создана в 14:00

### 8️⃣ Посмотреть сессии за последние 24 часа

```sql
SELECT * FROM digest_sessions 
WHERE created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;
```

**Разбор команды:**
- `NOW()` - текущая дата и время
- `INTERVAL '24 hours'` - интервал в 24 часа
- `NOW() - INTERVAL '24 hours'` = "24 часа назад от текущего момента"
- `>` = "больше чем" (то есть новее чем)

### 9️⃣ Посмотреть старые неактивные сессии (для очистки)

```sql
SELECT * FROM digest_sessions 
WHERE is_active = false 
AND updated_at < NOW() - INTERVAL '7 days';
```

**Разбор команды:**
- `AND` - логическое "И" (оба условия должны выполняться)
- Ищем сессии, которые:
  1. Неактивные (`is_active = false`)
  2. И (`AND`) обновлены более 7 дней назад

### 🔟 Посмотреть данные с красивым форматированием

```sql
SELECT 
    id,
    chat_id,
    news_count,
    CASE 
        WHEN is_active THEN 'Активна'
        ELSE 'Завершена'
    END as статус,
    TO_CHAR(created_at, 'DD.MM.YYYY HH24:MI') as создана
FROM digest_sessions
ORDER BY created_at DESC
LIMIT 10;
```

**Разбор команды:**
- `CASE WHEN ... THEN ... ELSE ... END` - условие (как if/else в программировании)
- Переводим `true`/`false` в понятные слова "Активна"/"Завершена"
- `TO_CHAR()` - форматирование даты
- `'DD.MM.YYYY HH24:MI'` - формат даты (день.месяц.год час:минуты)

**Пример вывода:**
```
 id |     chat_id      | news_count |   статус   |     создана      
----+------------------+------------+------------+------------------
  5 | -1002983482030   |         18 | Активна    | 01.10.2025 14:30
  4 | -1002983482030   |         21 | Завершена  | 01.10.2025 10:00
  3 | -1002983482030   |         15 | Завершена  | 30.09.2025 09:00
```

---

## 🎨 Способ 2: GUI-инструменты (графические программы)

Для начинающих **намного проще** использовать графические программы вместо терминала!

### 🔥 Рекомендуемые программы:

#### 1. **DBeaver** (Лучший выбор для начинающих!)

**Установка на macOS:**
```bash
brew install --cask dbeaver-community
```

**Как подключиться:**

1. Открыть DBeaver
2. Нажать "Database" → "New Database Connection"
3. Выбрать "PostgreSQL"
4. Заполнить поля:
   - **Host**: `localhost`
   - **Port**: `5432`
   - **Database**: `ai_news_db`
   - **Username**: `postgres`
   - **Password**: [ваш пароль из .env]
5. Нажать "Test Connection" (проверить подключение)
6. Если всё ОК - нажать "Finish"

**Преимущества DBeaver:**
- ✅ Бесплатный и открытый
- ✅ Простой и понятный интерфейс
- ✅ Автодополнение SQL-запросов
- ✅ Визуализация данных в виде таблицы
- ✅ Можно править данные прямо в таблице
- ✅ **Идеально для обучения!**

**Как использовать DBeaver:**

1. В левой панели раскройте дерево:
   ```
   PostgreSQL
   └── ai_news_db
       └── Schemas
           └── public
               └── Tables
                   └── digest_sessions  ← кликните правой кнопкой
   ```

2. Выберите "View Data" → Откроется таблица с данными!

3. Для SQL-запросов:
   - Нажмите `Cmd + ]` или "SQL Editor" → "New SQL Script"
   - Напишите запрос, например: `SELECT * FROM digest_sessions;`
   - Нажмите `Cmd + Enter` для выполнения

#### 2. **pgAdmin 4** (Официальный инструмент)

**Установка:**
```bash
brew install --cask pgadmin4
```

**Преимущества:**
- ✅ Официальный инструмент PostgreSQL
- ✅ Много возможностей
- ❌ Тяжеловесный
- ❌ Сложнее для начинающих

#### 3. **Postico** (только macOS, платный)

**Установка:**
```bash
brew install --cask postico
```

**Преимущества:**
- ✅ Самый красивый интерфейс
- ✅ Очень простой
- ❌ Платный ($40 после trial)
- ❌ Только для macOS

---

## 🎮 Практические примеры

### Сценарий 1: Проверить миграцию

После запуска утилиты миграции, проверьте:

```sql
-- 1. Посмотреть структуру таблицы
\d digest_sessions

-- 2. Посмотреть все мигрированные данные
SELECT * FROM digest_sessions;

-- 3. Подсчитать количество
SELECT COUNT(*) FROM digest_sessions;

-- 4. Проверить, есть ли активные сессии
SELECT * FROM digest_sessions WHERE is_active = true;
```

### Сценарий 2: Мониторинг после запуска бота

```sql
-- Посмотреть последние 10 сессий
SELECT 
    id,
    chat_id,
    news_count,
    is_active,
    created_at
FROM digest_sessions 
ORDER BY created_at DESC 
LIMIT 10;

-- Проверить активные сессии
SELECT COUNT(*) as активных 
FROM digest_sessions 
WHERE is_active = true;
```

### Сценарий 3: Отладка - найти "зависшие" сессии

```sql
-- Найти сессии, которые активны больше 1 дня
SELECT * FROM digest_sessions 
WHERE is_active = true 
AND created_at < NOW() - INTERVAL '1 day';
```

### Сценарий 4: Ручная очистка (если нужно)

```sql
-- ШАГ 1: Сначала ПОСМОТРЕТЬ, что будет удалено (БЕЗ удаления!)
SELECT * FROM digest_sessions 
WHERE is_active = false 
AND updated_at < NOW() - INTERVAL '7 days';

-- ШАГ 2: Если всё правильно - удалить
DELETE FROM digest_sessions 
WHERE is_active = false 
AND updated_at < NOW() - INTERVAL '7 days';

-- ШАГ 3: Проверить результат
SELECT COUNT(*) FROM digest_sessions;
```

⚠️ **ВАЖНО:** Всегда сначала делайте SELECT, чтобы увидеть, что будет изменено/удалено!

---

## 🛠️ Полезные команды

### Форматирование вывода

```sql
-- Включить расширенный вывод (каждое поле на новой строке)
\x

-- Теперь запрос покажет данные вертикально:
SELECT * FROM digest_sessions WHERE id = 1;

-- Вывод:
-[ RECORD 1 ]---------------------------------------
id          | 1
chat_id     | -1002983482030
message_ids | [237, 238, 239, 240]
news_count  | 21
is_active   | t
created_at  | 2025-10-01 09:00:00

-- Вернуть обычный вывод:
\x
```

### Включить показ времени выполнения

```sql
-- Включить таймер
\timing

-- Теперь каждый запрос покажет время:
SELECT COUNT(*) FROM news;
-- Time: 15.234 ms
```

### Информация о БД

```sql
-- Размер базы данных
SELECT pg_size_pretty(pg_database_size('ai_news_db'));

-- Количество записей во всех таблицах
SELECT 
    tablename as таблица,
    n_live_tup as записей
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;
```

---

## 🚨 Частые ошибки и решения

### Ошибка 1: "connection refused"

```
psql: could not connect to server: Connection refused
```

**Причина:** PostgreSQL не запущен

**Решение:**
```bash
# Проверить статус
brew services list | grep postgres

# Запустить PostgreSQL
brew services start postgresql@12
```

### Ошибка 2: "password authentication failed"

```
psql: FATAL: password authentication failed for user "postgres"
```

**Причина:** Неверный пароль

**Решение:** Проверьте пароль в файле `.env`:
```bash
cat .env | grep DATABASE
```

### Ошибка 3: "database does not exist"

```
psql: FATAL: database "ai_news_db" does not exist
```

**Причина:** База данных не создана

**Решение:**
```bash
# Войти в postgres
psql -U postgres

# Создать базу
CREATE DATABASE ai_news_db;

# Выйти
\q
```

### Ошибка 4: Забыли точку с запятой

```sql
SELECT * FROM digest_sessions
ai_news_db-# 
```

**Причина:** Забыли `;` в конце

**Решение:** Допишите `;` и нажмите Enter:
```sql
ai_news_db-# ;
```

---

## 💡 Советы для начинающих

### 1. Всегда используйте WHERE с UPDATE и DELETE

```sql
-- ❌ ПЛОХО: удалит ВСЕ данные!
DELETE FROM digest_sessions;

-- ✅ ХОРОШО: удалит только нужные
DELETE FROM digest_sessions WHERE id = 1;
```

### 2. Сначала SELECT, потом UPDATE/DELETE

```sql
-- Сначала посмотрите, что будет изменено:
SELECT * FROM digest_sessions WHERE is_active = true;

-- Если всё правильно - обновите:
UPDATE digest_sessions SET is_active = false WHERE is_active = true;
```

### 3. Используйте LIMIT для больших таблиц

```sql
-- Посмотреть первые 10 записей:
SELECT * FROM news LIMIT 10;
```

### 4. Используйте транзакции для безопасности

```sql
-- Начать транзакцию
BEGIN;

-- Выполнить изменения
UPDATE digest_sessions SET is_active = false WHERE id = 1;

-- Если всё хорошо - сохранить:
COMMIT;

-- Если нужно отменить:
ROLLBACK;
```

### 5. Делайте backup перед экспериментами

```bash
# Создать backup
pg_dump ai_news_db > backup_$(date +%Y%m%d).sql

# Восстановить из backup (если что-то пошло не так)
psql ai_news_db < backup_20251001.sql
```

---

## 📚 Шпаргалка команд

### Метакоманды psql

```sql
\l                          -- список баз данных
\c database_name            -- переключить базу
\dt                         -- список таблиц
\d table_name               -- структура таблицы
\du                         -- список пользователей
\x                          -- вертикальный вывод
\timing                     -- показывать время
\q                          -- выход
```

### SQL-запросы

```sql
-- ЧТЕНИЕ
SELECT * FROM table_name;
SELECT column1, column2 FROM table_name WHERE condition;
SELECT COUNT(*) FROM table_name;

-- ДОБАВЛЕНИЕ
INSERT INTO table_name (column1, column2) VALUES (value1, value2);

-- ИЗМЕНЕНИЕ
UPDATE table_name SET column1 = value1 WHERE condition;

-- УДАЛЕНИЕ
DELETE FROM table_name WHERE condition;

-- СОРТИРОВКА
ORDER BY column_name DESC;   -- от большего к меньшему
ORDER BY column_name ASC;    -- от меньшего к большему

-- ОГРАНИЧЕНИЕ
LIMIT 10;                    -- только 10 записей
```

---

## 🎯 Практическое задание для закрепления

Попробуйте выполнить эти задания по порядку:

### Задание 1: Подключение и навигация
```sql
-- 1. Подключитесь к БД через терминал
psql -h localhost -U postgres -d ai_news_db

-- 2. Посмотрите список таблиц
\dt

-- 3. Посмотрите структуру таблицы digest_sessions
\d digest_sessions
```

### Задание 2: Простые запросы
```sql
-- 4. Посмотрите все сессии
SELECT * FROM digest_sessions;

-- 5. Подсчитайте количество сессий
SELECT COUNT(*) FROM digest_sessions;

-- 6. Посмотрите только активные сессии
SELECT * FROM digest_sessions WHERE is_active = true;
```

### Задание 3: Более сложные запросы
```sql
-- 7. Посмотрите последние 5 сессий
SELECT * FROM digest_sessions ORDER BY created_at DESC LIMIT 5;

-- 8. Найдите сессии за последние 24 часа
SELECT * FROM digest_sessions 
WHERE created_at > NOW() - INTERVAL '24 hours';

-- 9. Статистика по статусам
SELECT 
    is_active,
    COUNT(*) as количество
FROM digest_sessions
GROUP BY is_active;
```

---

## 🎓 Рекомендации по обучению

### Шаг 1: Основы SQL (1-2 недели)
- [SQL Tutorial на W3Schools](https://www.w3schools.com/sql/) - интерактивный курс с примерами
- [PostgreSQL Tutorial](https://www.postgresqltutorial.com/) - специально для PostgreSQL

### Шаг 2: Практика (ежедневно)
- Выполняйте запросы к вашей БД
- Экспериментируйте с разными условиями WHERE
- Попробуйте разные варианты ORDER BY и LIMIT

### Шаг 3: GUI-инструменты (рекомендую начать с этого!)
- Установите DBeaver
- Подключитесь к БД
- Изучайте структуру таблиц визуально

---

## 🎉 Заключение

### Для ежедневной работы вам нужно знать всего 3 команды:

```bash
# 1. Подключиться
psql -h localhost -U postgres -d ai_news_db

# 2. Посмотреть активные сессии дайджестов
SELECT * FROM digest_sessions WHERE is_active = true;

# 3. Выйти
\q
```

### Или используйте DBeaver - это будет проще! 🚀

**DBeaver позволяет:**
- Видеть все таблицы визуально
- Редактировать данные прямо в таблице
- Выполнять SQL-запросы с подсветкой синтаксиса
- Сохранять часто используемые запросы

---

## 📞 Дополнительная помощь

Если у вас возникнут вопросы:

1. Проверьте логи бота: `tail -f bot_smoke.log`
2. Проверьте данные в БД с помощью запросов выше
3. Попробуйте DBeaver для визуального изучения

**Помните:** Бояться БД не нужно! Все данные можно восстановить из backup. Экспериментируйте и учитесь! 💪

---

**Создано:** 2025-10-01  
**Для проекта:** AI News Assistant  
**Версия:** 1.0 для начинающих разработчиков  
**Автор:** AI Assistant

