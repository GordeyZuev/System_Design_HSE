
CREATE SCHEMA IF NOT EXISTS staging;


CREATE TABLE IF NOT EXISTS staging.temp_users_staging (
    user_id UUID,
    email TEXT,
    phone TEXT,
    status TEXT,
    created_at TIMESTAMP
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

-- Аренды
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


CREATE TABLE IF NOT EXISTS staging.temp_rental_events_staging (
    event_id UUID,
    rental_id UUID,
    ts TIMESTAMP,
    event_type TEXT,
    payload JSONB
);

CREATE TABLE IF NOT EXISTS staging.temp_offer_audit_staging (
    id UUID,
    offer_id UUID,
    event_type TEXT,
    ts TIMESTAMP,
    payload_json JSONB
);
