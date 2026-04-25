-- Добавление поля alliance в таблицу collection_periods
ALTER TABLE collection_periods ADD COLUMN IF NOT EXISTS alliance TEXT;

-- Создание индекса для быстрого поиска по альянсу
CREATE INDEX IF NOT EXISTS idx_collection_periods_alliance ON collection_periods(alliance);

-- Обновление существующих записей (если есть) - устанавливаем дефолтный альянс
UPDATE collection_periods SET alliance = 'Альянс 1' WHERE alliance IS NULL;

-- Делаем поле обязательным
ALTER TABLE collection_periods ALTER COLUMN alliance SET NOT NULL;
