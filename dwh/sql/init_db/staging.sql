CREATE SCHEMA IF NOT EXISTS staging;


CREATE TABLE IF NOT EXISTS staging.temp_users_staging (
    user_id UUID,
    email TEXT,
    phone TEXT,
    status TEXT,
    created_at TIMESTAMP
);

INSERT INTO staging.temp_users_staging
SELECT
    '11111111-1111-1111-1111-111111111111',
    'test1@example.com',
    '+79990000001',
    'ACTIVE',
    NOW() - INTERVAL '10 days'
WHERE NOT EXISTS (
    SELECT 1 FROM staging.temp_users_staging
    WHERE user_id = '11111111-1111-1111-1111-111111111111'
);


CREATE TABLE IF NOT EXISTS staging.temp_offers_shard_0 (
    offer_id UUID,
    user_id UUID,
    station_id TEXT,
    tariff_snapshot JSONB,
    created_at TIMESTAMP,
    expires_at TIMESTAMP,
    status TEXT,
    tariff_version TEXT
);

INSERT INTO staging.temp_offers_shard_0
SELECT
    '22222222-2222-2222-2222-222222222222',
    '11111111-1111-1111-1111-111111111111',
    'station-001',
    '{"price_per_minute": 5, "currency": "RUB"}',
    NOW() - INTERVAL '1 day',
    NOW() + INTERVAL '1 day',
    'ACTIVE',
    'v1'
WHERE NOT EXISTS (
    SELECT 1 FROM staging.temp_offers_shard_0
    WHERE offer_id = '22222222-2222-2222-2222-222222222222'
);


CREATE TABLE IF NOT EXISTS staging.temp_offers_shard_1 (
    offer_id UUID,
    user_id UUID,
    station_id TEXT,
    tariff_snapshot JSONB,
    created_at TIMESTAMP,
    expires_at TIMESTAMP,
    status TEXT,
    tariff_version TEXT
);

INSERT INTO staging.temp_offers_shard_1
SELECT
    '33333333-3333-3333-3333-333333333333',
    '11111111-1111-1111-1111-111111111111',
    'station-002',
    '{"price_per_minute": 6, "currency": "RUB"}',
    NOW() - INTERVAL '2 days',
    NOW() + INTERVAL '1 day',
    'EXPIRED',
    'v1'
WHERE NOT EXISTS (
    SELECT 1 FROM staging.temp_offers_shard_1
    WHERE offer_id = '33333333-3333-3333-3333-333333333333'
);


CREATE TABLE IF NOT EXISTS staging.temp_rentals_shard_0 (
    rental_id UUID,
    offer_id UUID,
    user_id UUID,
    station_id TEXT,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    status TEXT,
    tariff_snapshot JSONB,
    tariff_version TEXT,
    final_cost NUMERIC(10,2)
);

INSERT INTO staging.temp_rentals_shard_0
SELECT
    '44444444-4444-4444-4444-444444444444',
    '22222222-2222-2222-2222-222222222222',
    '11111111-1111-1111-1111-111111111111',
    'station-001',
    NOW() - INTERVAL '3 hours',
    NOW() - INTERVAL '2 hours',
    'FINISHED',
    '{"price_per_minute": 5}',
    'v1',
    300.00
WHERE NOT EXISTS (
    SELECT 1 FROM staging.temp_rentals_shard_0
    WHERE rental_id = '44444444-4444-4444-4444-444444444444'
);


CREATE TABLE IF NOT EXISTS staging.temp_rentals_shard_1 (
    rental_id UUID,
    offer_id UUID,
    user_id UUID,
    station_id TEXT,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    status TEXT,
    tariff_snapshot JSONB,
    tariff_version TEXT,
    final_cost NUMERIC(10,2)
);

INSERT INTO staging.temp_rentals_shard_1
SELECT
    '55555555-5555-5555-5555-555555555555',
    '33333333-3333-3333-3333-333333333333',
    '11111111-1111-1111-1111-111111111111',
    'station-002',
    NOW() - INTERVAL '5 hours',
    NOW() - INTERVAL '4 hours',
    'FINISHED',
    '{"price_per_minute": 6}',
    'v1',
    360.00
WHERE NOT EXISTS (
    SELECT 1 FROM staging.temp_rentals_shard_1
    WHERE rental_id = '55555555-5555-5555-5555-555555555555'
);


CREATE TABLE IF NOT EXISTS staging.temp_rental_events_staging (
    event_id UUID UNIQUE PRIMARY KEY,
    rental_id UUID,
    ts TIMESTAMP,
    event_type TEXT,
    payload JSONB
);

INSERT INTO staging.temp_rental_events_staging
SELECT
    gen_random_uuid(),
    '44444444-4444-4444-4444-444444444444',
    NOW() - INTERVAL '2 hours',
    'RENTAL_FINISHED',
    '{"reason": "normal"}'
WHERE NOT EXISTS (
    SELECT 1 FROM staging.temp_rental_events_staging
    WHERE rental_id = '44444444-4444-4444-4444-444444444444'
);


CREATE TABLE IF NOT EXISTS staging.temp_offer_audit_staging (
    id UUID PRIMARY KEY,
    offer_id UUID,
    event_type TEXT,
    ts TIMESTAMP,
    payload_json JSONB
);

INSERT INTO staging.temp_offer_audit_staging
SELECT
    gen_random_uuid(),
    '22222222-2222-2222-2222-222222222222',
    'OFFER_CREATED',
    NOW() - INTERVAL '1 day',
    '{"source": "seed"}'
WHERE NOT EXISTS (
    SELECT 1 FROM staging.temp_offer_audit_staging
    WHERE offer_id = '22222222-2222-2222-2222-222222222222'
);
