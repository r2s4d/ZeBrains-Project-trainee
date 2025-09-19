-- Скрипт для настройки полных прав доступа для bot_user
-- Запуск: psql -h localhost -U postgres -d ai_news_assistant -f scripts/setup_db_permissions.sql

-- 1. Предоставляем права на все существующие таблицы
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bot_user;

-- 2. Предоставляем права на все существующие последовательности
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO bot_user;

-- 3. Предоставляем права на все существующие функции
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO bot_user;

-- 4. Предоставляем права на схему public
GRANT USAGE ON SCHEMA public TO bot_user;

-- 5. Устанавливаем права по умолчанию для БУДУЩИХ объектов
-- Это гарантирует, что новые таблицы автоматически будут доступны bot_user

-- Права на будущие таблицы
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO bot_user;

-- Права на будущие последовательности
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO bot_user;

-- Права на будущие функции
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON FUNCTIONS TO bot_user;

-- 6. Проверяем результат
SELECT 
    'Таблицы' as object_type,
    COUNT(*) as count
FROM information_schema.table_privileges 
WHERE grantee = 'bot_user' AND privilege_type = 'SELECT'

UNION ALL

SELECT 
    'Последовательности' as object_type,
    COUNT(*) as count
FROM information_schema.usage_privileges 
WHERE grantee = 'bot_user' AND object_type = 'SEQUENCE'

UNION ALL

SELECT 
    'Функции' as object_type,
    COUNT(*) as count
FROM information_schema.routine_privileges 
WHERE grantee = 'bot_user';

-- 7. Показываем все таблицы, к которым теперь есть доступ
SELECT DISTINCT table_name 
FROM information_schema.table_privileges 
WHERE grantee = 'bot_user' AND privilege_type = 'SELECT'
ORDER BY table_name;

