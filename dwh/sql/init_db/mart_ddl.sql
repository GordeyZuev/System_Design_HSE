CREATE SCHEMA IF NOT EXISTS mart;

CREATE MATERIALIZED VIEW mart.dm_daily_metrics AS
SELECT 
    d.date_actual,
    d.year,
    d.month_num,
    d.day_of_week,
    d.is_weekend,
    
    -- Метрики по арендам
    COUNT(DISTINCT fr.rental_id) AS total_rentals,
    COUNT(DISTINCT CASE WHEN fr.is_completed THEN fr.rental_id END) AS completed_rentals,
    COUNT(DISTINCT CASE WHEN fr.is_cancelled THEN fr.rental_id END) AS cancelled_rentals,
    COUNT(DISTINCT fr.user_dwh_id) AS active_users,
    
    -- Метрики по выручке
    SUM(fr.final_cost) AS total_revenue,
    AVG(fr.final_cost) AS avg_rental_cost,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fr.final_cost) AS median_rental_cost,
    
    -- Метрики по длительности
    AVG(fr.duration_minutes) AS avg_duration_minutes,
    SUM(fr.duration_minutes) AS total_duration_minutes,
    
    -- Метрики по офферам
    COUNT(DISTINCT fo.offer_id) AS total_offers_created,
    COUNT(DISTINCT CASE WHEN fo.is_used THEN fo.offer_id END) AS offers_used,
    COUNT(DISTINCT CASE WHEN fo.is_expired_unused THEN fo.offer_id END) AS offers_expired,
    
    -- Конверсия
    ROUND(
        100.0 * COUNT(DISTINCT CASE WHEN fo.is_used THEN fo.offer_id END) / 
        NULLIF(COUNT(DISTINCT fo.offer_id), 0), 
        2
    ) AS offer_to_rental_conversion_rate
    
FROM dds.dim_date d
LEFT JOIN dds.fact_rentals fr ON d.date_id = fr.start_date_id
LEFT JOIN dds.fact_offers fo ON d.date_id = fo.created_date_id
WHERE d.date_actual >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY d.date_actual, d.year, d.month_num, d.day_of_week, d.is_weekend
ORDER BY d.date_actual DESC;

CREATE UNIQUE INDEX idx_dm_daily_metrics_date ON mart.dm_daily_metrics(date_actual);




CREATE MATERIALIZED VIEW mart.dm_station_stats AS
SELECT 
    s.station_id,
    s.station_name,
    s.city,
    
    -- Период анализа (последние 30 дней)
    COUNT(DISTINCT fr.rental_id) AS total_rentals_30d,
    COUNT(DISTINCT fr.user_dwh_id) AS unique_users_30d,
    
    -- Выручка
    SUM(fr.final_cost) AS total_revenue_30d,
    AVG(fr.final_cost) AS avg_rental_cost,
    
    -- Использование
    AVG(fr.duration_minutes) AS avg_duration_minutes,
    SUM(fr.duration_minutes) AS total_usage_minutes_30d,
    
    -- Тренды
    COUNT(DISTINCT CASE 
        WHEN fr.start_date_id >= TO_CHAR(CURRENT_DATE - INTERVAL '7 days', 'YYYYMMDD')::INTEGER 
        THEN fr.rental_id 
    END) AS rentals_last_7d,
    
    -- Рейтинг
    RANK() OVER (ORDER BY COUNT(DISTINCT fr.rental_id) DESC) AS popularity_rank
    
FROM dds.dim_stations s
LEFT JOIN dds.fact_rentals fr ON s.station_dwh_id = fr.station_dwh_id
WHERE fr.start_date_id >= TO_CHAR(CURRENT_DATE - INTERVAL '30 days', 'YYYYMMDD')::INTEGER
GROUP BY s.station_id, s.station_name, s.city
ORDER BY total_rentals_30d DESC;

CREATE UNIQUE INDEX idx_dm_station_stats_station_id ON mart.dm_station_stats(station_id);





CREATE MATERIALIZED VIEW mart.dm_user_cohorts AS
SELECT 
    DATE_TRUNC('month', u.user_created_at) AS cohort_month,
    COUNT(DISTINCT u.user_dwh_id) AS cohort_size,
    
    -- Retention анализ
    COUNT(DISTINCT CASE 
        WHEN fr.start_date_id >= TO_CHAR(DATE_TRUNC('month', u.user_created_at), 'YYYYMMDD')::INTEGER
         AND fr.start_date_id < TO_CHAR(DATE_TRUNC('month', u.user_created_at) + INTERVAL '1 month', 'YYYYMMDD')::INTEGER
        THEN u.user_dwh_id 
    END) AS active_month_0,
    
    COUNT(DISTINCT CASE 
        WHEN fr.start_date_id >= TO_CHAR(DATE_TRUNC('month', u.user_created_at) + INTERVAL '1 month', 'YYYYMMDD')::INTEGER
         AND fr.start_date_id < TO_CHAR(DATE_TRUNC('month', u.user_created_at) + INTERVAL '2 month', 'YYYYMMDD')::INTEGER
        THEN u.user_dwh_id 
    END) AS active_month_1,
    
    -- Средние метрики когорты
    AVG(rental_counts.total_rentals) AS avg_rentals_per_user,
    AVG(rental_counts.total_spent) AS avg_revenue_per_user
    
FROM dds.dim_users u
LEFT JOIN (
    SELECT 
        user_dwh_id,
        COUNT(*) AS total_rentals,
        SUM(final_cost) AS total_spent
    FROM dds.fact_rentals
    WHERE is_completed = TRUE
    GROUP BY user_dwh_id
) rental_counts ON u.user_dwh_id = rental_counts.user_dwh_id
WHERE u.is_current = TRUE
  AND u.user_created_at >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '12 months'
GROUP BY DATE_TRUNC('month', u.user_created_at)
ORDER BY cohort_month DESC;






CREATE MATERIALIZED VIEW mart.dm_hourly_demand AS
SELECT 
    t.hour,
    t.hour_of_day,
    d.is_weekend,
    
    COUNT(DISTINCT fr.rental_id) AS total_rentals,
    AVG(fr.final_cost) AS avg_cost,
    AVG(fr.duration_minutes) AS avg_duration
    
FROM dds.dim_time t
CROSS JOIN (SELECT DISTINCT is_weekend FROM dds.dim_date) d
LEFT JOIN dds.fact_rentals fr 
    ON t.time_id = fr.start_time_id
   AND d.is_weekend = (SELECT is_weekend FROM dds.dim_date WHERE date_id = fr.start_date_id)
WHERE fr.start_date_id >= TO_CHAR(CURRENT_DATE - INTERVAL '30 days', 'YYYYMMDD')::INTEGER
GROUP BY t.hour, t.hour_of_day, d.is_weekend
ORDER BY d.is_weekend, t.hour;



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