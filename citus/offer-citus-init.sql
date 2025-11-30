-- Включаем расширение Citus в базе offer
--SET citus.enable_ddl_propagation TO off;

\c offer_db

CREATE EXTENSION IF NOT EXISTS citus;

CREATE TYPE IF NOT EXISTS offer_status AS ENUM ('ACTIVE', 'USED', 'EXPIRED', 'CANCELLED');

--ALTER SYSTEM SET citus.connection_password = 'adminpass';
--ALTER SYSTEM SET citus.remote_conninfo = 'user=postgres password=adminpass';
INSERT INTO pg_dist_authinfo (nodeid, rolename, authinfo) VALUES
  (1, 'postgres', 'password=adminpass'),
  (2, 'postgres', 'password=adminpass');

--CREATE USER citus WITH PASSWORK 'cituspass';
--GRANT ALL PRIVILEGES ON DATABASE offer_db TO citus;
SELECT pg_reload_conf();

-- Добавляем воркеры в кластер offer
SELECT * FROM master_add_node('offer-citus-worker-1', 5432);
SELECT * FROM master_add_node('offer-citus-worker-2', 5432);

-- Настройки для шардирования
SET citus.shard_count = 3;
SET citus.shard_replication_factor = 1;

CREATE TABLE offers (
    id BIGSERIAL,
    user_id BIGINT NOT NULL,
    title TEXT NOT NULL,
    status offer_status DEFAULT 'ACTIVE',
    price DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT NOW()
);

SELECT create_distributed_table('offers', 'user_id');

--SET citus.enable_ddl_propagation TO on;
SELECT * FROM master_get_active_worker_nodes();

