DROP SCHEMA IF EXISTS dds CASCADE;
CREATE SCHEMA dds;


CREATE TABLE dds.dim_users (
    user_dwh_id SERIAL PRIMARY KEY,
    user_id UUID UNIQUE NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    status VARCHAR(50),
    user_created_at TIMESTAMP,
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
    station_name VARCHAR(255),
    city VARCHAR(100),
    region VARCHAR(100),
    latitude NUMERIC(10, 8),
    longitude NUMERIC(11, 8),
    dw_loaded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_dim_stations_station_id ON dds.dim_stations(station_id);
CREATE INDEX idx_dim_stations_city ON dds.dim_stations(city);



CREATE TABLE dds.dim_date (
    date_id INTEGER PRIMARY KEY,
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
    is_holiday BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_dim_date_date_actual ON dds.dim_date(date_actual);
CREATE INDEX idx_dim_date_year_month ON dds.dim_date(year, month_num);


TRUNCATE dds.dim_date;


INSERT INTO dds.dim_date (
    date_id, date_actual, day_of_week, day_name, day_of_month,
    week_of_year, month_num, month_name, quarter, year, is_weekend
)
SELECT
    TO_CHAR(d, 'YYYYMMDD')::INTEGER AS date_id,
    d AS date_actual,
    EXTRACT(ISODOW FROM d) AS day_of_week,
    TO_CHAR(d, 'Day') AS day_name,
    EXTRACT(DAY FROM d) AS day_of_month,
    EXTRACT(WEEK FROM d) AS week_of_year,
    EXTRACT(MONTH FROM d) AS month_num,
    TO_CHAR(d, 'Month') AS month_name,
    EXTRACT(QUARTER FROM d) AS quarter,
    EXTRACT(YEAR FROM d) AS year,
    CASE WHEN EXTRACT(ISODOW FROM d) IN (6, 7) THEN TRUE ELSE FALSE END AS is_weekend
FROM generate_series(
    DATE '2020-01-01',
    DATE '2030-12-31',
    INTERVAL '1 day'
) AS d
ON CONFLICT DO NOTHING;


CREATE TABLE dds.dim_time (
    time_id INTEGER PRIMARY KEY,
    time_actual TIME NOT NULL UNIQUE,
    hour INTEGER,
    minute INTEGER,
    hour_of_day VARCHAR(20),
    is_business_hours BOOLEAN
);

CREATE INDEX idx_dim_time_hour ON dds.dim_time(hour);



INSERT INTO dds.dim_time (
    time_id,
    time_actual,
    hour,
    minute,
    hour_of_day,
    is_business_hours
)
SELECT
    (h * 10000 + m * 100)::INTEGER AS time_id,
    MAKE_TIME(h, m, 0) AS time_actual,
    h AS hour,
    m AS minute,
    CASE 
        WHEN h BETWEEN 9 AND 17 THEN 'Business Hours'
        ELSE 'Outside Hours'
    END AS hour_of_day,
    (h BETWEEN 9 AND 17) AS is_business_hours
FROM
    generate_series(0, 23) AS h,
    generate_series(0, 59) AS m
ORDER BY h, m
ON CONFLICT DO NOTHING;


CREATE TABLE dds.dim_tariff (
    tariff_dwh_id SERIAL PRIMARY KEY,
    tariff_version VARCHAR(50) NOT NULL,
    tariff_snapshot JSONB NOT NULL,
    rate_per_minute NUMERIC(10, 4),
    currency VARCHAR(10),
    tariff_type VARCHAR(50),

    valid_from TIMESTAMP,
    valid_to TIMESTAMP DEFAULT '9999-12-31',
    dw_loaded_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tariff_version, rate_per_minute)
);

CREATE INDEX idx_dim_tariff_version ON dds.dim_tariff(tariff_version);
CREATE INDEX idx_dim_tariff_type ON dds.dim_tariff(tariff_type);



CREATE TABLE dds.fact_rentals (
    rental_dwh_id SERIAL,
    rental_id UUID PRIMARY KEY,
    
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
    dw_updated_at TIMESTAMP DEFAULT NOW()
);



CREATE TABLE dds.fact_offers (
    offer_dwh_id SERIAL,
    offer_id UUID PRIMARY KEY,
    
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
    
    dw_loaded_at TIMESTAMP DEFAULT NOW()
);
