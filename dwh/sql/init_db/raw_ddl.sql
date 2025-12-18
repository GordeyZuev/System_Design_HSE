CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE raw.users (
    raw_id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    status VARCHAR(50),
    created_at TIMESTAMP,
    loaded_at TIMESTAMP DEFAULT NOW(),
    source_system VARCHAR(50) DEFAULT 'user_service'
);
CREATE INDEX idx_raw_users_loaded_at ON raw.users(loaded_at);


CREATE TABLE raw.offers (
    raw_id SERIAL PRIMARY KEY,
    offer_id UUID NOT NULL,
    user_id UUID NOT NULL,
    station_id VARCHAR(255) NOT NULL,
    tariff_snapshot JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    status VARCHAR(50) NOT NULL,
    tariff_version VARCHAR(50),
    shard_id INTEGER,
    loaded_at TIMESTAMP DEFAULT NOW(),
    source_system VARCHAR(50) DEFAULT 'offer_service'
) PARTITION BY RANGE (loaded_at);

CREATE INDEX idx_raw_offers_loaded_at ON raw.offers(loaded_at);
CREATE INDEX idx_raw_offers_offer_id ON raw.offers(offer_id);


CREATE TABLE raw.rentals (
    raw_id SERIAL PRIMARY KEY,
    rental_id UUID NOT NULL,
    offer_id UUID NOT NULL,
    user_id UUID NOT NULL,
    station_id VARCHAR(255) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    finished_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) NOT NULL,
    tariff_snapshot JSONB NOT NULL,
    tariff_version VARCHAR(50),
    final_cost NUMERIC(10, 2),
    shard_id INTEGER,
    loaded_at TIMESTAMP DEFAULT NOW(),
    source_system VARCHAR(50) DEFAULT 'rental_service'
) PARTITION BY RANGE (loaded_at);

CREATE INDEX idx_raw_rentals_loaded_at ON raw.rentals(loaded_at);
CREATE INDEX idx_raw_rentals_rental_id ON raw.rentals(rental_id);



CREATE TABLE raw.rental_events (
    raw_id SERIAL PRIMARY KEY,
    event_id UUID NOT NULL,
    rental_id UUID NOT NULL,
    ts TIMESTAMP WITH TIME ZONE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB,
    loaded_at TIMESTAMP DEFAULT NOW()
) PARTITION BY RANGE (ts);

CREATE INDEX idx_raw_rental_events_ts ON raw.rental_events(ts);
CREATE INDEX idx_raw_rental_events_rental_id ON raw.rental_events(rental_id);



CREATE TABLE raw.offer_audit (
    raw_id SERIAL PRIMARY KEY,
    id UUID NOT NULL,
    offer_id UUID NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    ts TIMESTAMP NOT NULL,
    payload_json JSONB,
    loaded_at TIMESTAMP DEFAULT NOW()
) PARTITION BY RANGE (ts);

CREATE INDEX idx_raw_offer_audit_ts ON raw.offer_audit(ts);
