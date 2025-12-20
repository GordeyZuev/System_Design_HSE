from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'dwh_team',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'refresh_mart_layer',
    default_args=default_args,
    description='Refresh Data Marts (Materialized Views)',
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
) as dag:

    create_marts = PostgresOperator(
        task_id='create_mart_views',
        postgres_conn_id='dwh_postgres',
        sql="""
        CREATE SCHEMA IF NOT EXISTS mart;

        -- dm_daily_metrics
        CREATE MATERIALIZED VIEW IF NOT EXISTS mart.dm_daily_metrics AS
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
        GROUP BY d.date_actual, d.year, d.month_num, d.day_of_week, d.is_weekend;

        CREATE UNIQUE INDEX IF NOT EXISTS idx_dm_daily_metrics_date 
            ON mart.dm_daily_metrics(date_actual);


        CREATE MATERIALIZED VIEW IF NOT EXISTS mart.dm_station_stats AS
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
        GROUP BY s.station_id, s.station_name, s.city;

        CREATE UNIQUE INDEX IF NOT EXISTS idx_dm_station_stats_station_id 
            ON mart.dm_station_stats(station_id);

        """,
        do_xcom_push=False
    )


    refresh_daily_metrics = PostgresOperator(
        task_id='refresh_dm_daily_metrics',
        postgres_conn_id='dwh_postgres',
        sql="REFRESH MATERIALIZED VIEW mart.dm_daily_metrics;",
        do_xcom_push=False
    )

    refresh_station_stats = PostgresOperator(
        task_id='refresh_dm_station_stats',
        postgres_conn_id='dwh_postgres',
        sql="REFRESH MATERIALIZED VIEW mart.dm_station_stats;",
        do_xcom_push=False
    )

    refresh_user_cohorts = PostgresOperator(
        task_id='refresh_dm_user_cohorts',
        postgres_conn_id='dwh_postgres',
        sql="REFRESH MATERIALIZED VIEW mart.dm_user_cohorts;",
        do_xcom_push=False
    )

    refresh_hourly_demand = PostgresOperator(
        task_id='refresh_dm_hourly_demand',
        postgres_conn_id='dwh_postgres',
        sql="REFRESH MATERIALIZED VIEW mart.dm_hourly_demand;",
        do_xcom_push=False
    )

    refresh_revenue_breakdown = PostgresOperator(
        task_id='refresh_dm_revenue_breakdown',
        postgres_conn_id='dwh_postgres',
        sql="REFRESH MATERIALIZED VIEW mart.dm_revenue_breakdown;",
        do_xcom_push=False
    )


    create_marts >> [
        refresh_daily_metrics,
        refresh_station_stats,
        refresh_user_cohorts,
        refresh_hourly_demand,
        refresh_revenue_breakdown
    ]