-- Добавляем поле для оценки релевантности новости
ALTER TABLE news ADD COLUMN ai_relevance_score INTEGER DEFAULT NULL;

-- Добавляем комментарий к полю
COMMENT ON COLUMN news.ai_relevance_score IS 'AI-оценка релевантности новости (0-10)';
