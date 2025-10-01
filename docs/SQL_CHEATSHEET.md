# 📋 SQL Шпаргалка для AI News Assistant

## 🚀 Быстрый старт

### Подключение к БД
```bash
psql -h localhost -U postgres -d ai_news_db
```

### Выход из БД
```sql
\q
```

---

## 📊 Проверка сессий дайджестов

### Посмотреть все активные сессии
```sql
SELECT * FROM digest_sessions WHERE is_active = true;
```

### Посмотреть последние 10 сессий
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

### Подсчитать количество активных сессий
```sql
SELECT COUNT(*) FROM digest_sessions WHERE is_active = true;
```

### Статистика по сессиям
```sql
SELECT 
    is_active,
    COUNT(*) as количество,
    MAX(created_at) as последняя
FROM digest_sessions
GROUP BY is_active;
```

---

## 🔍 Поиск и фильтрация

### Сессии за последние 24 часа
```sql
SELECT * FROM digest_sessions 
WHERE created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;
```

### Сессии для конкретного чата
```sql
SELECT * FROM digest_sessions 
WHERE chat_id = '-1002983482030';
```

### Старые неактивные сессии (старше 7 дней)
```sql
SELECT * FROM digest_sessions 
WHERE is_active = false 
AND updated_at < NOW() - INTERVAL '7 days';
```

---

## 🛠️ Полезные метакоманды

```sql
\dt                    -- список всех таблиц
\d digest_sessions     -- структура таблицы
\x                     -- вертикальный вывод (вкл/выкл)
\timing                -- показывать время выполнения
\q                     -- выход
```

---

## 📱 GUI-инструменты (рекомендуется для начинающих)

### Установка DBeaver (самый простой)
```bash
brew install --cask dbeaver-community
```

**Подключение:**
- Host: `localhost`
- Port: `5432`
- Database: `ai_news_db`
- Username: `postgres`
- Password: [из .env файла]

---

## 🎯 Частые задачи

### Проверить миграцию
```sql
-- Посмотреть структуру
\d digest_sessions

-- Посмотреть данные
SELECT * FROM digest_sessions;

-- Подсчитать количество
SELECT COUNT(*) FROM digest_sessions;
```

### Мониторинг после запуска бота
```sql
-- Активные сессии сейчас
SELECT COUNT(*) FROM digest_sessions WHERE is_active = true;

-- Сессии созданные сегодня
SELECT * FROM digest_sessions WHERE created_at >= CURRENT_DATE;
```

### Отладка зависших сессий
```sql
-- Найти активные сессии старше 1 дня
SELECT * FROM digest_sessions 
WHERE is_active = true 
AND created_at < NOW() - INTERVAL '1 day';
```

---

## ⚠️ Важные правила

1. **Всегда используйте WHERE с DELETE/UPDATE**
   ```sql
   -- ❌ ПЛОХО: удалит ВСЁ
   DELETE FROM digest_sessions;
   
   -- ✅ ХОРОШО: удалит только нужное
   DELETE FROM digest_sessions WHERE id = 1;
   ```

2. **Сначала SELECT, потом DELETE/UPDATE**
   ```sql
   -- Посмотреть, что будет удалено
   SELECT * FROM digest_sessions WHERE is_active = false;
   
   -- Если всё правильно - удалить
   DELETE FROM digest_sessions WHERE is_active = false;
   ```

3. **Используйте LIMIT для больших таблиц**
   ```sql
   SELECT * FROM news LIMIT 10;
   ```

---

## 💾 Backup и восстановление

### Создать backup
```bash
pg_dump ai_news_db > backup_$(date +%Y%m%d).sql
```

### Восстановить из backup
```bash
psql ai_news_db < backup_20251001.sql
```

---

## 🎨 Красивое форматирование

### Вертикальный вывод для длинных записей
```sql
\x
SELECT * FROM digest_sessions WHERE id = 1;
\x
```

### Дата в читаемом формате
```sql
SELECT 
    id,
    chat_id,
    TO_CHAR(created_at, 'DD.MM.YYYY HH24:MI') as дата
FROM digest_sessions;
```

---

## 📞 Помощь

- Полное руководство: [DATABASE_BEGINNER_GUIDE.md](DATABASE_BEGINNER_GUIDE.md)
- Миграция: [MIGRATION_DIGEST_SESSIONS_GUIDE.md](../MIGRATION_DIGEST_SESSIONS_GUIDE.md)

---

**Версия:** 1.0  
**Проект:** AI News Assistant

