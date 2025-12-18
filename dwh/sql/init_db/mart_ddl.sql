-- Создание схемы mart
CREATE SCHEMA IF NOT EXISTS mart;

-- MATERIALIZED VIEW: dm_daily_metrics
CREATE MATERIALIZED VIEW mart.dm_daily_metrics AS
SELECT 
    d.date_actual,
    d.year,
    d.month_num,
    d.day_of_week,
    d.is_weekend,
    
    COUNT(DISTINCT fr.rental_id) AS total_rentals,
    COUNT(DISTINCT CASE WHEN fr.is_completed THEN fr.rental_id END) AS completed_rentals,
    COUNT(DISTINCT CASE WHEN fr.is_cancelled THEN fr.rental_id END) AS cancelled_rentals,
    COUNT(DISTINCT fr.user_dwh_id) AS active_users,
    
    SUM(fr.final_cost) AS total_revenue,
    AVG(fr.final_cost) AS avg_rental_cost,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fr.final_cost) AS median_rental_cost,
    
    AVG(fr.duration_minutes) AS avg_duration_minutes,
    SUM(fr.duration_minutes) AS total_duration_minutes,
    
    COUNT(DISTINCT fo.offer_id) AS total_offers_created,
    COUNT(DISTINCT CASE WHEN fo.is_used THEN fo.offer_id END) AS offers_used,
    COUNT(DISTINCT CASE WHEN fo.is_expired_unused THEN fo.offer_id END) AS offers_expired,
    
    ROUND(
        100.0 * COUNT(DISTINCT CASE WHEN fo.is_used THEN fo.offer_id END) / NULLIF(COUNT(DISTINCT fo.offer_id),0), 
        2
    ) AS offer_to_rental_conversion_rate

FROM dds.dim_date d
LEFT JOIN dds.fact_rentals fr ON d.date_id = fr.start_date_id
LEFT JOIN dds.fact_offers fo ON d.date_id = fo.created_date_id
WHERE d.date_actual >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY d.date_actual, d.year, d.month_num, d.day_of_week, d.is_weekend
ORDER BY d.date_actual DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_dm_daily_metrics_date 
    ON mart.dm_daily_metrics(date_actual);


-- MATERIALIZED VIEW: dm_station_stats
CREATE MATERIALIZED VIEW mart.dm_station_stats AS
WITH rentals_30d AS (
    SELECT 
        fr.station_dwh_id,
        fr.rental_id,
        fr.user_dwh_id,
        fr.final_cost,
        fr.duration_minutes,
        fr.start_date_id
    FROM dds.fact_rentals fr
    WHERE fr.start_date_id >= TO_CHAR(CURRENT_DATE - INTERVAL '30 days','YYYYMMDD')::INTEGER
)
SELECT 
    s.station_id,
    s.station_name,
    s.city,
    COUNT(DISTINCT r.rental_id) AS total_rentals_30d,
    COUNT(DISTINCT r.user_dwh_id) AS unique_users_30d,
    SUM(r.final_cost) AS total_revenue_30d,
    AVG(r.final_cost) AS avg_rental_cost,
    AVG(r.duration_minutes) AS avg_duration_minutes,
    SUM(r.duration_minutes) AS total_usage_minutes_30d,
    COUNT(DISTINCT CASE WHEN r.start_date_id >= TO_CHAR(CURRENT_DATE - INTERVAL '7 days','YYYYMMDD')::INTEGER THEN r.rental_id END) AS rentals_last_7d,
    RANK() OVER (ORDER BY COUNT(DISTINCT r.rental_id) DESC) AS popularity_rank
FROM dds.dim_stations s
LEFT JOIN rentals_30d r ON s.station_dwh_id = r.station_dwh_id
GROUP BY s.station_id, s.station_name, s.city
ORDER BY total_rentals_30d DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_dm_station_stats_station_id 
    ON mart.dm_station_stats(station_id);


-- MATERIALIZED VIEW: dm_user_cohorts
CREATE MATERIALIZED VIEW mart.dm_user_cohorts AS
WITH rental_counts AS (
    SELECT 
        user_dwh_id,
        COUNT(*) AS total_rentals,
        SUM(final_cost) AS total_spent
    FROM dds.fact_rentals
    WHERE is_completed = TRUE
    GROUP BY user_dwh_id
)
SELECT 
    DATE_TRUNC('month', u.user_created_at) AS cohort_month,
    COUNT(DISTINCT u.user_dwh_id) AS cohort_size,
    COUNT(DISTINCT CASE 
        WHEN fr.start_date_id >= TO_CHAR(DATE_TRUNC('month', u.user_created_at),'YYYYMMDD')::INTEGER
         AND fr.start_date_id < TO_CHAR(DATE_TRUNC('month', u.user_created_at) + INTERVAL '1 month','YYYYMMDD')::INTEGER
        THEN u.user_dwh_id
    END) AS active_month_0,
    COUNT(DISTINCT CASE 
        WHEN fr.start_date_id >= TO_CHAR(DATE_TRUNC('month', u.user_created_at) + INTERVAL '1 month','YYYYMMDD')::INTEGER
         AND fr.start_date_id < TO_CHAR(DATE_TRUNC('month', u.user_created_at) + INTERVAL '2 month','YYYYMMDD')::INTEGER
        THEN u.user_dwh_id
    END) AS active_month_1,
    AVG(rc.total_rentals) AS avg_rentals_per_user,
    AVG(rc.total_spent) AS avg_revenue_per_user
FROM dds.dim_users u
LEFT JOIN rental_counts rc ON u.user_dwh_id = rc.user_dwh_id
LEFT JOIN dds.fact_rentals fr ON u.user_dwh_id = fr.user_dwh_id
WHERE u.is_current = TRUE
  AND u.user_created_at >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '12 months'
GROUP BY DATE_TRUNC('month', u.user_created_at)
ORDER BY cohort_month DESC;


-- MATERIALIZED VIEW: dm_hourly_demand
CREATE MATERIALIZED VIEW mart.dm_hourly_demand AS
WITH rentals_30d AS (
    SELECT fr.start_time_id, fr.start_date_id, fr.rental_id, fr.final_cost, fr.duration_minutes
    FROM dds.fact_rentals fr
    WHERE fr.start_date_id >= TO_CHAR(CURRENT_DATE - INTERVAL '30 days','YYYYMMDD')::INTEGER
)
SELECT 
    t.hour,
    t.hour_of_day,
    d.is_weekend,
    COUNT(DISTINCT r.rental_id) AS total_rentals,
    AVG(r.final_cost) AS avg_cost,
    AVG(r.duration_minutes) AS avg_duration
FROM dds.dim_time t
CROSS JOIN (SELECT DISTINCT is_weekend FROM dds.dim_date) d
LEFT JOIN rentals_30d r 
    JOIN dds.dim_date dd ON r.start_date_id = dd.date_id
    ON t.time_id = r.start_time_id AND dd.is_weekend = d.is_weekend
GROUP BY t.hour, t.hour_of_day, d.is_weekend
ORDER BY d.is_weekend, t.hour;


-- MATERIALIZED VIEW: dm_revenue_breakdown
CREATE MATERIALIZED VIEW mart.dm_revenue_breakdown AS
SELECT 
    DATE_TRUNC('day', d.date_actual) AS date,
    tariff.tariff_type,
    s.city,
    COUNT(DISTINCT fr.rental_id) AS rentals_count,
    SUM(fr.final_cost) AS revenue,
    AVG(fr.final_cost) AS avg_revenue_per_rental,
    SUM(fr.duration_minutes) AS total_minutes
FROM dds.fact_rentals fr
JOIN dds.dim_date d ON fr.start_date_id = d.date_id
JOIN dds.dim_tariff tariff ON fr.tariff_dwh_id = tariff.tariff_dwh_id
JOIN dds.dim_stations s ON fr.station_dwh_id = s.station_dwh_id
WHERE d.date_actual >= CURRENT_DATE - INTERVAL '90 days'
  AND fr.is_completed = TRUE
GROUP BY DATE_TRUNC('day', d.date_actual), tariff.tariff_type, s.city
ORDER BY date DESC, revenue DESC;
