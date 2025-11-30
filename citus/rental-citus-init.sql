-- Включаем расширение Citus в базе rental_cmd
CREATE EXTENSION IF NOT EXISTS citus;

-- Добавляем воркеры в кластер rental
SELECT * FROM master_add_node('rental-citus-worker-1', 5432);
SELECT * FROM master_add_node('rental-citus-worker-2', 5432);

-- Настройки для шардирования
SET citus.shard_count = 32;
SET citus.shard_replication_factor = 1;
