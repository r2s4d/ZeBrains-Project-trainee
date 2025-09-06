-- Миграция: Добавление новых полей для расширенного AI анализа
-- Дата: 19 августа 2025
-- Описание: Добавляем поля для анализа актуальности, свежести и дубликатов

-- Добавляем новые поля в таблицу news
ALTER TABLE news 
ADD COLUMN IF NOT EXISTS relevance_score INTEGER DEFAULT 5,
ADD COLUMN IF NOT EXISTS freshness_score INTEGER DEFAULT 5,
ADD COLUMN IF NOT EXISTS ai_is_duplicate BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS ai_original_news_id INTEGER DEFAULT NULL,
ADD COLUMN IF NOT EXISTS ai_event_date VARCHAR(100) DEFAULT NULL,
ADD COLUMN IF NOT EXISTS ai_time_context VARCHAR(50) DEFAULT 'Не определен';

-- Добавляем комментарии к новым полям
COMMENT ON COLUMN news.relevance_score IS 'Оценка актуальности новости (1-10)';
COMMENT ON COLUMN news.freshness_score IS 'Оценка свежести новости (1-10)';
COMMENT ON COLUMN news.ai_is_duplicate IS 'Флаг дубликата по AI анализу';
COMMENT ON COLUMN news.ai_original_news_id IS 'ID оригинальной новости (если дубликат)';
COMMENT ON COLUMN news.ai_event_date IS 'Дата события по AI анализу';
COMMENT ON COLUMN news.ai_time_context IS 'Временной контекст события';

-- Создаем индекс для быстрого поиска по актуальности
CREATE INDEX IF NOT EXISTS idx_news_relevance_score ON news(relevance_score);

-- Создаем индекс для быстрого поиска по свежести
CREATE INDEX IF NOT EXISTS idx_news_freshness_score ON news(freshness_score);

-- Создаем индекс для поиска дубликатов
CREATE INDEX IF NOT EXISTS idx_news_ai_is_duplicate ON news(ai_is_duplicate);

-- Обновляем существующие записи, устанавливая значения по умолчанию
UPDATE news 
SET 
    relevance_score = 5,
    freshness_score = 5,
    ai_is_duplicate = FALSE,
    ai_time_context = 'Не определен'
WHERE relevance_score IS NULL;

-- Проверяем результат
SELECT 
    COUNT(*) as total_news,
    AVG(relevance_score) as avg_relevance,
    AVG(freshness_score) as avg_freshness,
    COUNT(*) FILTER (WHERE ai_is_duplicate = TRUE) as duplicate_count
FROM news;
