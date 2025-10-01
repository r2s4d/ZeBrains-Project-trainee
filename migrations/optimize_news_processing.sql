-- Migration: optimize_news_processing
-- Description: Добавляет индексы для оптимизации поиска дубликатов и проверки уникальности
-- Date: 2025-10-01
-- Author: AI News Assistant Team

-- ===================================================================
-- ИНДЕКСЫ ДЛЯ ОПТИМИЗАЦИИ ПРОВЕРКИ УНИКАЛЬНОСТИ НОВОСТЕЙ
-- ===================================================================

-- Индекс для быстрой проверки уникальности по message_id и каналу
-- Используется в NewsParserService.is_news_already_processed()
-- Ускоряет поиск с O(n) до O(log n)
CREATE INDEX IF NOT EXISTS idx_news_message_channel 
ON news(source_message_id, source_channel_username)
WHERE source_message_id IS NOT NULL;

COMMENT ON INDEX idx_news_message_channel IS 
'Быстрая проверка уникальности новостей по message_id и каналу. Предотвращает повторную обработку.';

-- ===================================================================
-- ИНДЕКСЫ ДЛЯ ОПТИМИЗАЦИИ ПОИСКА ДУБЛИКАТОВ
-- ===================================================================

-- Индекс для быстрого поиска релевантных новостей за последние 24 часа
-- Используется в DuplicateDetectionService._get_candidate_news()
-- Поддерживает фильтрацию по времени создания и релевантности
CREATE INDEX IF NOT EXISTS idx_news_created_relevant 
ON news(created_at DESC, ai_relevance_score)
WHERE ai_relevance_score >= 6 AND status != 'deleted';

COMMENT ON INDEX idx_news_created_relevant IS 
'Оптимизация поиска кандидатов для сравнения дубликатов. Только релевантные новости за последние 24 часа.';

-- Индекс для быстрого поиска по статусу и времени создания
-- Используется для общих запросов к новостям
CREATE INDEX IF NOT EXISTS idx_news_status_created 
ON news(status, created_at DESC)
WHERE status != 'deleted';

COMMENT ON INDEX idx_news_status_created IS 
'Общий индекс для фильтрации новостей по статусу и времени создания.';

-- ===================================================================
-- ИНДЕКСЫ ДЛЯ ОПТИМИЗАЦИИ РАБОТЫ С ИСТОЧНИКАМИ
-- ===================================================================

-- Индекс для быстрой проверки существующих связей новость-источник
-- Используется в DuplicateDetectionService.merge_duplicate_sources()
-- Предотвращает создание дублирующих связей
CREATE INDEX IF NOT EXISTS idx_news_sources_composite 
ON news_sources(news_id, source_id);

COMMENT ON INDEX idx_news_sources_composite IS 
'Быстрая проверка существующих связей между новостями и источниками. Предотвращает дубликаты.';

-- Индекс для обратного поиска (от источника к новостям)
CREATE INDEX IF NOT EXISTS idx_news_sources_source_id 
ON news_sources(source_id, news_id);

COMMENT ON INDEX idx_news_sources_source_id IS 
'Обратный индекс для поиска всех новостей по источнику.';

-- ===================================================================
-- СТАТИСТИКА И МОНИТОРИНГ
-- ===================================================================

-- Обновляем статистику таблиц для оптимизатора запросов
ANALYZE news;
ANALYZE news_sources;

-- ===================================================================
-- ПРОВЕРКА СОЗДАННЫХ ИНДЕКСОВ
-- ===================================================================

-- Проверяем, что все индексы созданы успешно
DO $$
DECLARE
    idx_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO idx_count
    FROM pg_indexes
    WHERE schemaname = 'public'
    AND indexname IN (
        'idx_news_message_channel',
        'idx_news_created_relevant',
        'idx_news_status_created',
        'idx_news_sources_composite',
        'idx_news_sources_source_id'
    );
    
    IF idx_count = 5 THEN
        RAISE NOTICE '✅ Все 5 индексов успешно созданы';
    ELSE
        RAISE WARNING '⚠️ Создано только % из 5 индексов', idx_count;
    END IF;
END $$;

-- ===================================================================
-- ПРИМЕР ИСПОЛЬЗОВАНИЯ
-- ===================================================================

-- Пример 1: Проверка уникальности новости (используется индекс idx_news_message_channel)
-- EXPLAIN ANALYZE
-- SELECT * FROM news 
-- WHERE source_message_id = 12345 
-- AND source_channel_username = 'ai_news';

-- Пример 2: Поиск кандидатов для дубликатов (используется индекс idx_news_created_relevant)
-- EXPLAIN ANALYZE
-- SELECT * FROM news 
-- WHERE created_at >= NOW() - INTERVAL '24 hours'
-- AND ai_relevance_score >= 6
-- AND status != 'deleted'
-- LIMIT 50;

-- Пример 3: Проверка существующей связи (используется индекс idx_news_sources_composite)
-- EXPLAIN ANALYZE
-- SELECT * FROM news_sources 
-- WHERE news_id = 123 
-- AND source_id = 456;

-- ===================================================================
-- ОТКАТ МИГРАЦИИ (если нужно)
-- ===================================================================

-- DROP INDEX IF EXISTS idx_news_message_channel;
-- DROP INDEX IF EXISTS idx_news_created_relevant;
-- DROP INDEX IF EXISTS idx_news_status_created;
-- DROP INDEX IF EXISTS idx_news_sources_composite;
-- DROP INDEX IF EXISTS idx_news_sources_source_id;

