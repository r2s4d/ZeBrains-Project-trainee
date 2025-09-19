-- Миграция: Создание таблицы bot_sessions для хранения состояний бота
-- Дата: 2025-01-27
-- Описание: Таблица для хранения всех состояний бота в БД вместо памяти

-- Создаем таблицу bot_sessions
CREATE TABLE IF NOT EXISTS bot_sessions (
    id SERIAL PRIMARY KEY,
    session_type VARCHAR(50) NOT NULL,
    user_id VARCHAR(50),
    chat_id VARCHAR(50),
    data TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создаем индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_bot_sessions_type_user ON bot_sessions(session_type, user_id);
CREATE INDEX IF NOT EXISTS idx_bot_sessions_expires_at ON bot_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_bot_sessions_status ON bot_sessions(status);
CREATE INDEX IF NOT EXISTS idx_bot_sessions_chat_id ON bot_sessions(chat_id);

-- Добавляем комментарии к таблице и колонкам
COMMENT ON TABLE bot_sessions IS 'Состояния бота для устойчивости к перезапускам';
COMMENT ON COLUMN bot_sessions.session_type IS 'Тип сессии: digest_edit, photo_wait, expert_session, curator_moderation, current_digest, interactive_moderation';
COMMENT ON COLUMN bot_sessions.user_id IS 'ID пользователя/эксперта (может быть пустым для системных сессий)';
COMMENT ON COLUMN bot_sessions.chat_id IS 'ID чата (может быть пустым для пользовательских сессий)';
COMMENT ON COLUMN bot_sessions.data IS 'JSON строка с данными сессии';
COMMENT ON COLUMN bot_sessions.status IS 'Статус сессии: active, completed, expired, cancelled';
COMMENT ON COLUMN bot_sessions.expires_at IS 'Время истечения сессии для автоочистки';

-- Создаем функцию для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_bot_sessions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Создаем триггер для автоматического обновления updated_at
DROP TRIGGER IF EXISTS update_bot_sessions_updated_at ON bot_sessions;
CREATE TRIGGER update_bot_sessions_updated_at
    BEFORE UPDATE ON bot_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_bot_sessions_updated_at();

-- Вставляем тестовые данные для проверки
INSERT INTO bot_sessions (session_type, user_id, data, status, expires_at) VALUES
('test_session', '123456789', '{"test": true, "message": "Тестовая сессия"}', 'active', NOW() + INTERVAL '1 hour')
ON CONFLICT DO NOTHING;

-- Выводим информацию о созданной таблице
SELECT 
    'bot_sessions' as table_name,
    COUNT(*) as total_sessions,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_sessions,
    COUNT(CASE WHEN expires_at < NOW() THEN 1 END) as expired_sessions
FROM bot_sessions;
