-- Миграция: Создание таблицы digest_sessions для хранения сессий дайджеста
-- Дата: 2024-01-XX
-- Описание: Добавляет таблицу для отслеживания сообщений дайджеста в Telegram чатах

-- Создаем таблицу digest_sessions
CREATE TABLE IF NOT EXISTS digest_sessions (
    id SERIAL PRIMARY KEY,
    chat_id VARCHAR(255) NOT NULL,
    message_ids TEXT NOT NULL,  -- JSON строка с ID сообщений
    news_count INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Создаем индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_digest_sessions_chat_id ON digest_sessions(chat_id);
CREATE INDEX IF NOT EXISTS idx_digest_sessions_is_active ON digest_sessions(is_active);
CREATE INDEX IF NOT EXISTS idx_digest_sessions_created_at ON digest_sessions(created_at);

-- Добавляем комментарии к таблице
COMMENT ON TABLE digest_sessions IS 'Сессии дайджеста для отслеживания сообщений в Telegram чатах';
COMMENT ON COLUMN digest_sessions.chat_id IS 'ID чата в Telegram';
COMMENT ON COLUMN digest_sessions.message_ids IS 'JSON строка с массивом ID сообщений дайджеста';
COMMENT ON COLUMN digest_sessions.news_count IS 'Количество новостей в дайджесте';
COMMENT ON COLUMN digest_sessions.is_active IS 'Флаг активности сессии';

-- Проверяем, что таблица создана
SELECT 'Таблица digest_sessions создана успешно' as status;
