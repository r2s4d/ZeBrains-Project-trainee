-- Миграция для добавления полей AI анализа в таблицу news
-- Выполнить: psql -h localhost -U ai_news_user -d ai_news_assistant -f migrate_ai_fields.sql

-- Добавляем новые поля для AI анализа
ALTER TABLE news ADD COLUMN IF NOT EXISTS ai_summary TEXT;
ALTER TABLE news ADD COLUMN IF NOT EXISTS importance_score VARCHAR(10);
ALTER TABLE news ADD COLUMN IF NOT EXISTS category VARCHAR(100);
ALTER TABLE news ADD COLUMN IF NOT EXISTS tags TEXT;
ALTER TABLE news ADD COLUMN IF NOT EXISTS potential_impact TEXT;
ALTER TABLE news ADD COLUMN IF NOT EXISTS tone VARCHAR(20);
ALTER TABLE news ADD COLUMN IF NOT EXISTS ai_analyzed_at TIMESTAMP;

-- Добавляем комментарии к полям
COMMENT ON COLUMN news.ai_summary IS 'AI-генерированное саммари новости';
COMMENT ON COLUMN news.importance_score IS 'Оценка важности от 0.0 до 10.0';
COMMENT ON COLUMN news.category IS 'Категория новости (например: Машинное обучение, Робототехника)';
COMMENT ON COLUMN news.tags IS 'Теги для классификации (через запятую)';
COMMENT ON COLUMN news.potential_impact IS 'Оценка потенциального влияния на индустрию';
COMMENT ON COLUMN news.tone IS 'Тональность новости (Позитивная/Негативная/Нейтральная)';
COMMENT ON COLUMN news.ai_analyzed_at IS 'Дата и время выполнения AI анализа';

-- Создаем индекс для быстрого поиска по категориям
CREATE INDEX IF NOT EXISTS idx_news_category ON news(category);

-- Создаем индекс для поиска по важности
CREATE INDEX IF NOT EXISTS idx_news_importance ON news(importance_score);

-- Обновляем существующие записи (если есть)
UPDATE news SET 
    ai_summary = title,
    importance_score = '5.0',
    category = 'Общие технологии ИИ',
    tags = 'ИИ, Технологии',
    potential_impact = 'Может повлиять на развитие технологий ИИ.',
    tone = 'Нейтральная',
    ai_analyzed_at = NOW()
WHERE ai_summary IS NULL;

-- Проверяем результат
SELECT 
    COUNT(*) as total_news,
    COUNT(ai_summary) as with_ai_summary,
    COUNT(category) as with_category,
    COUNT(importance_score) as with_importance_score
FROM news;
