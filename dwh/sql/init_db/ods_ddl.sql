CREATE SCHEMA IF NOT EXISTS ods;

CREATE TABLE ods.users (
    user_id UUID PRIMARY KEY,
    email VARCHAR(255),
    phone VARCHAR(50),
    status VARCHAR(50),
    created_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    dw_loaded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ods_users_updated_at ON ods.users(updated_at);
CREATE INDEX idx_ods_users_status ON ods.users(status);


CREATE TABLE ods.offers (
    offer_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    station_id VARCHAR(255) NOT NULL,
    tariff_snapshot JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    status VARCHAR(50) NOT NULL,
    tariff_version VARCHAR(50),
    tariff_rate_per_minute NUMERIC(10, 4), -- extracted from JSON
    tariff_currency VARCHAR(10), -- extracted from JSON
    updated_at TIMESTAMP DEFAULT NOW(),
    dw_loaded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ods_offers_user_id ON ods.offers(user_id);
CREATE INDEX idx_ods_offers_station_id ON ods.offers(station_id);
CREATE INDEX idx_ods_offers_status ON ods.offers(status);
CREATE INDEX idx_ods_offers_created_at ON ods.offers(created_at);


CREATE TABLE ods.rentals (
    rental_id UUID PRIMARY KEY,
    offer_id UUID NOT NULL,
    user_id UUID NOT NULL,
    station_id VARCHAR(255) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    finished_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) NOT NULL,
    tariff_snapshot JSONB NOT NULL,
    tariff_version VARCHAR(50),
    final_cost NUMERIC(10, 2),
    duration_minutes INTEGER, -- calculated field
    updated_at TIMESTAMP DEFAULT NOW(),
    dw_loaded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ods_rentals_user_id ON ods.rentals(user_id);
CREATE INDEX idx_ods_rentals_offer_id ON ods.rentals(offer_id);
CREATE INDEX idx_ods_rentals_station_id ON ods.rentals(station_id);
CREATE INDEX idx_ods_rentals_started_at ON ods.rentals(started_at);
CREATE INDEX idx_ods_rentals_status ON ods.rentals(status);
