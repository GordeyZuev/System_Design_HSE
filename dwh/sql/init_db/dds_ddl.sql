DROP SCHEMA IF EXISTS dds CASCADE;
CREATE SCHEMA dds;


CREATE TABLE dds.dim_users (
    user_dwh_id SERIAL PRIMARY KEY,
    user_id UUID UNIQUE NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    status VARCHAR(50),
    user_created_at TIMESTAMP,
    -- SCD Type 2 fields
    valid_from TIMESTAMP NOT NULL DEFAULT NOW(),
    valid_to TIMESTAMP DEFAULT '9999-12-31',
    is_current BOOLEAN DEFAULT TRUE,
    dw_loaded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_dim_users_user_id ON dds.dim_users(user_id);
CREATE INDEX idx_dim_users_is_current ON dds.dim_users(is_current);
CREATE INDEX idx_dim_users_status ON dds.dim_users(status) WHERE is_current = TRUE;



CREATE TABLE dds.dim_stations (
    station_dwh_id SERIAL PRIMARY KEY,
    station_id VARCHAR(255) UNIQUE NOT NULL,
    station_name VARCHAR(255), -- можно обогатить из внешнего справочника
    city VARCHAR(100),
    region VARCHAR(100),
    -- Для будущего обогащения
    latitude NUMERIC(10, 8),
    longitude NUMERIC(11, 8),
    dw_loaded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_dim_stations_station_id ON dds.dim_stations(station_id);
CREATE INDEX idx_dim_stations_city ON dds.dim_stations(city);



CREATE TABLE dds.dim_date (
    date_id INTEGER PRIMARY KEY, -- YYYYMMDD
    date_actual DATE NOT NULL UNIQUE,
    day_of_week INTEGER,
    day_name VARCHAR(10),
    day_of_month INTEGER,
    week_of_year INTEGER,
    month_num INTEGER,
    month_name VARCHAR(10),
    quarter INTEGER,
    year INTEGER,
    is_weekend BOOLEAN,
    is_holiday BOOLEAN DEFAULT FALSE -- можно обогатить календарём праздников
);

CREATE INDEX idx_dim_date_date_actual ON dds.dim_date(date_actual);
CREATE INDEX idx_dim_date_year_month ON dds.dim_date(year, month_num);


CREATE TABLE dds.dim_time (
    time_id INTEGER PRIMARY KEY, -- HHMMSS (e.g., 143000 for 14:30:00)
    time_actual TIME NOT NULL UNIQUE,
    hour INTEGER,
    minute INTEGER,
    hour_of_day VARCHAR(20), -- '00-06', '06-12', '12-18', '18-24'
    is_business_hours BOOLEAN -- 09:00-18:00
);

CREATE INDEX idx_dim_time_hour ON dds.dim_time(hour);



CREATE TABLE dds.dim_tariff (
    tariff_dwh_id SERIAL PRIMARY KEY,
    tariff_version VARCHAR(50) NOT NULL,
    tariff_snapshot JSONB NOT NULL,
    rate_per_minute NUMERIC(10, 4),
    currency VARCHAR(10),
    tariff_type VARCHAR(50), -- 'standard', 'premium', 'promo'
    -- Для анализа
    valid_from TIMESTAMP,
    valid_to TIMESTAMP DEFAULT '9999-12-31',
    dw_loaded_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tariff_version, rate_per_minute)
);

CREATE INDEX idx_dim_tariff_version ON dds.dim_tariff(tariff_version);
CREATE INDEX idx_dim_tariff_type ON dds.dim_tariff(tariff_type);



CREATE TABLE dds.fact_rentals (
    rental_dwh_id SERIAL,  -- просто уникальный идентификатор
    rental_id UUID NOT NULL,
    
    user_dwh_id INTEGER REFERENCES dds.dim_users(user_dwh_id),
    station_dwh_id INTEGER REFERENCES dds.dim_stations(station_dwh_id),
    start_date_id INTEGER REFERENCES dds.dim_date(date_id),
    start_time_id INTEGER REFERENCES dds.dim_time(time_id),
    end_date_id INTEGER REFERENCES dds.dim_date(date_id),
    end_time_id INTEGER REFERENCES dds.dim_time(time_id),
    tariff_dwh_id INTEGER REFERENCES dds.dim_tariff(tariff_dwh_id),
    
    offer_id UUID NOT NULL,
    
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    finished_at TIMESTAMP WITH TIME ZONE,
    duration_minutes INTEGER,
    final_cost NUMERIC(10, 2),
    status VARCHAR(50),
    
    is_completed BOOLEAN GENERATED ALWAYS AS (status = 'FINISHED') STORED,
    is_cancelled BOOLEAN GENERATED ALWAYS AS (status = 'CANCELLED') STORED,
    
    dw_loaded_at TIMESTAMP DEFAULT NOW(),
    dw_updated_at TIMESTAMP DEFAULT NOW(),
    
    PRIMARY KEY (rental_id, start_date_id)
) PARTITION BY RANGE (start_date_id);



CREATE TABLE dds.fact_offers (
    offer_dwh_id SERIAL,
    offer_id UUID NOT NULL,
    
    user_dwh_id INTEGER REFERENCES dds.dim_users(user_dwh_id),
    station_dwh_id INTEGER REFERENCES dds.dim_stations(station_dwh_id),
    created_date_id INTEGER REFERENCES dds.dim_date(date_id),
    created_time_id INTEGER REFERENCES dds.dim_time(time_id),
    tariff_dwh_id INTEGER REFERENCES dds.dim_tariff(tariff_dwh_id),
    
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    status VARCHAR(50),
    
    ttl_seconds INTEGER,
    is_used BOOLEAN GENERATED ALWAYS AS (status = 'USED') STORED,
    is_expired_unused BOOLEAN GENERATED ALWAYS AS (status = 'EXPIRED') STORED,
    
    dw_loaded_at TIMESTAMP DEFAULT NOW(),
    
    PRIMARY KEY (offer_id, created_date_id)  -- PK включает колонку партиции
) PARTITION BY RANGE (created_date_id);
