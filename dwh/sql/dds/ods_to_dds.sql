
INSERT INTO dds.dim_date (date_id, date_actual, day_of_week, day_name, day_of_month,
                          week_of_year, month_num, month_name, quarter, year, is_weekend)
SELECT
    to_char(d, 'YYYYMMDD')::int AS date_id,
    d AS date_actual,
    EXTRACT(ISODOW FROM d)::int AS day_of_week,
    to_char(d, 'Day') AS day_name,
    EXTRACT(DAY FROM d)::int AS day_of_month,
    EXTRACT(WEEK FROM d)::int AS week_of_year,
    EXTRACT(MONTH FROM d)::int AS month_num,
    to_char(d, 'Month') AS month_name,
    EXTRACT(QUARTER FROM d)::int AS quarter,
    EXTRACT(YEAR FROM d)::int AS year,
    CASE WHEN EXTRACT(DOW FROM d) IN (0,6) THEN TRUE ELSE FALSE END AS is_weekend
FROM generate_series(
    (SELECT MIN(started_at)::date FROM ods.rentals),
    (SELECT MAX(COALESCE(finished_at, started_at))::date FROM ods.rentals),
    '1 day'
) d
ON CONFLICT (date_id) DO NOTHING;


INSERT INTO dds.dim_time (time_id, time_actual, hour, minute, hour_of_day, is_business_hours)
SELECT
    (EXTRACT(HOUR FROM t)*10000 + EXTRACT(MINUTE FROM t)*100 + EXTRACT(SECOND FROM t))::int AS time_id,
    t AS time_actual,
    EXTRACT(HOUR FROM t)::int AS hour,
    EXTRACT(MINUTE FROM t)::int AS minute,
    CASE 
        WHEN EXTRACT(HOUR FROM t) BETWEEN 0 AND 5 THEN '00-06'
        WHEN EXTRACT(HOUR FROM t) BETWEEN 6 AND 11 THEN '06-12'
        WHEN EXTRACT(HOUR FROM t) BETWEEN 12 AND 17 THEN '12-18'
        ELSE '18-24'
    END AS hour_of_day,
    CASE WHEN EXTRACT(HOUR FROM t) BETWEEN 9 AND 18 THEN TRUE ELSE FALSE END AS is_business_hours
FROM generate_series(
    '00:00:00'::time,
    '23:59:00'::time,
    '1 minute'
) t
ON CONFLICT (time_id) DO NOTHING;


WITH source AS (
    SELECT *
    FROM ods.users
    WHERE dw_loaded_at > COALESCE((SELECT MAX(dw_loaded_at) FROM dds.dim_users), '1900-01-01')
)
INSERT INTO dds.dim_users (user_id, email, phone, status, user_created_at, valid_from)
SELECT s.user_id, s.email, s.phone, s.status, s.created_at, now()
FROM source s
ON CONFLICT (user_id, valid_from) DO NOTHING;


UPDATE dds.dim_users d
SET is_current = FALSE,
    valid_to = now()
FROM ods.users o
WHERE d.user_id = o.user_id
  AND d.is_current = TRUE
  AND (d.email <> o.email OR d.phone <> o.phone OR d.status <> o.status);



INSERT INTO dds.dim_stations (station_id, station_name, city, region, latitude, longitude)
SELECT DISTINCT
    station_id, station_name, city, region, latitude, longitude
FROM ods.rentals r
ON CONFLICT (station_id) DO UPDATE
SET station_name = EXCLUDED.station_name,
    city = EXCLUDED.city,
    region = EXCLUDED.region,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude;



WITH source AS (
    SELECT DISTINCT
        tariff_version,
        tariff_snapshot,
        (tariff_snapshot->>'rate_per_minute')::numeric AS rate_per_minute,
        tariff_snapshot->>'currency' AS currency,
        now() AS valid_from
    FROM ods.offers
)
INSERT INTO dds.dim_tariff (tariff_version, tariff_snapshot, rate_per_minute, currency, valid_from)
SELECT s.tariff_version, s.tariff_snapshot, s.rate_per_minute, s.currency, s.valid_from
FROM source s
ON CONFLICT (tariff_version, rate_per_minute, valid_from) DO NOTHING;


INSERT INTO dds.fact_rentals (
    rental_id,
    user_dwh_id,
    station_dwh_id,
    start_date_id,
    start_time_id,
    end_date_id,
    end_time_id,
    tariff_dwh_id,
    offer_id,
    started_at,
    finished_at,
    duration_minutes,
    final_cost,
    status
)
SELECT
    r.rental_id,
    u.user_dwh_id,
    s.station_dwh_id,
    to_char(r.started_at,'YYYYMMDD')::int,
    (EXTRACT(HOUR FROM r.started_at)*10000 + EXTRACT(MINUTE FROM r.started_at)*100 + EXTRACT(SECOND FROM r.started_at))::int,
    to_char(r.finished_at,'YYYYMMDD')::int,
    (EXTRACT(HOUR FROM r.finished_at)*10000 + EXTRACT(MINUTE FROM r.finished_at)*100 + EXTRACT(SECOND FROM r.finished_at))::int,
    t.tariff_dwh_id,
    r.offer_id,
    r.started_at,
    r.finished_at,
    CASE WHEN r.finished_at IS NOT NULL
         THEN EXTRACT(EPOCH FROM (r.finished_at - r.started_at))/60
         ELSE NULL
    END::int,
    r.final_cost,
    r.status
FROM ods.rentals r
JOIN dds.dim_users u ON r.user_id = u.user_id AND u.is_current = TRUE
JOIN dds.dim_stations s ON r.station_id = s.station_id
JOIN dds.dim_tariff t ON r.tariff_version = t.tariff_version;


INSERT INTO dds.fact_offers (
    offer_id,
    user_dwh_id,
    station_dwh_id,
    created_date_id,
    created_time_id,
    tariff_dwh_id,
    created_at,
    expires_at,
    status,
    ttl_seconds
)
SELECT
    o.offer_id,
    u.user_dwh_id,
    s.station_dwh_id,
    to_char(o.created_at,'YYYYMMDD')::int,
    (EXTRACT(HOUR FROM o.created_at)*10000 + EXTRACT(MINUTE FROM o.created_at)*100 + EXTRACT(SECOND FROM o.created_at))::int,
    t.tariff_dwh_id,
    o.created_at,
    o.expires_at,
    o.status,
    EXTRACT(EPOCH FROM (o.expires_at - o.created_at))::int
FROM ods.offers o
JOIN dds.dim_users u ON o.user_id = u.user_id AND u.is_current = TRUE
JOIN dds.dim_stations s ON o.station_id = s.station_id
JOIN dds.dim_tariff t ON o.tariff_version = t.tariff_version;
