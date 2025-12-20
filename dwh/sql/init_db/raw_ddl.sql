CREATE SCHEMA IF NOT EXISTS raw;


CREATE TABLE raw.users (
    raw_id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL UNIQUE,
    email VARCHAR(255),
    phone VARCHAR(50),
    status VARCHAR(50),
    created_at TIMESTAMP,
    loaded_at TIMESTAMP DEFAULT NOW(),
    source_system VARCHAR(50) DEFAULT 'user_service'
);

CREATE INDEX idx_raw_users_loaded_at ON raw.users(loaded_at);


CREATE TABLE raw.offers (
    offer_id UUID NOT NULL,
    user_id UUID,
    station_id TEXT,
    tariff_snapshot JSONB,
    created_at TIMESTAMP,
    expires_at TIMESTAMP,
    status TEXT,
    tariff_version TEXT,
    shard_id INT,
    loaded_at TIMESTAMP NOT NULL,
    source_system VARCHAR(50),
    PRIMARY KEY (offer_id, loaded_at)
);

CREATE INDEX idx_raw_offers_loaded_at ON raw.offers(loaded_at);
CREATE INDEX idx_raw_offers_offer_id ON raw.offers(offer_id);


CREATE TABLE raw.rentals (
    raw_id SERIAL,
    rental_id UUID NOT NULL,
    offer_id UUID NOT NULL,
    user_id UUID NOT NULL,
    station_id TEXT,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    finished_at TIMESTAMP WITH TIME ZONE,
    status TEXT,
    tariff_snapshot JSONB NOT NULL,
    tariff_version TEXT,
    final_cost NUMERIC(10, 2),
    shard_id INTEGER,
    loaded_at TIMESTAMP NOT NULL,
    source_system TEXT DEFAULT 'rental_service',
    PRIMARY KEY (rental_id, loaded_at)
);

CREATE INDEX idx_raw_rentals_loaded_at ON raw.rentals(loaded_at);
CREATE INDEX idx_raw_rentals_rental_id ON raw.rentals(rental_id);


CREATE TABLE raw.rental_events (
    raw_id SERIAL,
    event_id UUID PRIMARY KEY,
    rental_id UUID NOT NULL,
    ts TIMESTAMP WITH TIME ZONE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB,
    loaded_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_raw_rental_events_ts ON raw.rental_events(ts);
CREATE INDEX idx_raw_rental_events_rental_id ON raw.rental_events(rental_id);


CREATE TABLE raw.offer_audit (
    raw_id SERIAL,
    id UUID PRIMARY KEY,
    offer_id UUID NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    ts TIMESTAMP NOT NULL,
    payload_json JSONB,
    loaded_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_raw_offer_audit_ts ON raw.offer_audit(ts);
