from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator
from datetime import datetime

with DAG(
    'load_dds_layer',
    default_args={'owner': 'dwh_team'},
    description='Load DDS layer (Dimensional Model)',
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
) as dag:

    load_dim_users = PostgresOperator(
        task_id='load_dim_users',
        postgres_conn_id='dwh_postgres',
        sql="""

        UPDATE dds.dim_users du
        SET valid_to = NOW(), is_current = FALSE
        FROM ods.users ou
        WHERE ou.user_id = du.user_id
          AND du.is_current = TRUE
          AND ou.updated_at > du.valid_from
          AND (ou.email != du.email OR ou.phone != du.phone OR ou.status != du.status);


        INSERT INTO dds.dim_users (user_id, email, phone, status, user_created_at, dw_loaded_at)
        SELECT 
            ou.user_id,
            ou.email,
            ou.phone,
            ou.status,
            ou.created_at,
            NOW()
            
        FROM ods.users ou
        LEFT JOIN dds.dim_users du ON ou.user_id = du.user_id AND du.is_current = TRUE
        WHERE du.user_id IS NULL
           OR (ou.email != du.email OR ou.phone != du.phone OR ou.status != du.status);
        """,
        do_xcom_push=False
    )

    load_dim_stations = PostgresOperator(
        task_id='load_dim_stations',
        postgres_conn_id='dwh_postgres',
        sql="""
        INSERT INTO dds.dim_stations (station_id, station_name, city)
        SELECT station_id, station_name, city
        FROM ods.stations
        ON CONFLICT (station_id) DO UPDATE SET
            station_name = EXCLUDED.station_name,
            city = EXCLUDED.city,
            dw_loaded_at = NOW();
        """,
        do_xcom_push=False
    )

    load_dim_tariff = PostgresOperator(
        task_id='load_dim_tariff',
        postgres_conn_id='dwh_postgres',
        sql="""
        INSERT INTO dds.dim_tariff (tariff_version, tariff_snapshot, rate_per_minute, currency, tariff_type, valid_from)
        SELECT DISTINCT
            tariff_version,
            tariff_snapshot,
            (tariff_snapshot->>'price_per_minute')::NUMERIC(10,4) AS rate_per_minute,
            (tariff_snapshot->>'currency')::VARCHAR(10) AS currency,
            'standard' AS tariff_type,  -- или извлекайте из JSON
            MIN(created_at) AS valid_from
        FROM ods.offers
        WHERE tariff_version IS NOT NULL
        GROUP BY tariff_version, tariff_snapshot
        ON CONFLICT (tariff_version, rate_per_minute) DO UPDATE SET
            tariff_snapshot = EXCLUDED.tariff_snapshot,
            currency = EXCLUDED.currency,
            tariff_type = EXCLUDED.tariff_type,
            valid_from = EXCLUDED.valid_from;
        """,
        do_xcom_push=False
    )

    load_fact_rentals = PostgresOperator(
        task_id='load_fact_rentals',
        postgres_conn_id='dwh_postgres',
        sql="""
        INSERT INTO dds.fact_rentals (
            rental_id, user_dwh_id, station_dwh_id, 
            start_date_id, start_time_id, end_date_id, end_time_id, tariff_dwh_id,
            offer_id, started_at, finished_at, duration_minutes, final_cost, status, dw_updated_at
        )
        SELECT 
            r.rental_id,
            du.user_dwh_id,
            ds.station_dwh_id,
            TO_CHAR(r.started_at, 'YYYYMMDD')::INTEGER,
            (TO_CHAR(r.started_at, 'HH24MI') || '00')::INTEGER,
            CASE WHEN r.finished_at IS NOT NULL THEN TO_CHAR(r.finished_at, 'YYYYMMDD')::INTEGER END,
            CASE WHEN r.finished_at IS NOT NULL THEN (TO_CHAR(r.finished_at, 'HH24MI') || '00')::INTEGER END,
            dt.tariff_dwh_id,
            r.offer_id,
            r.started_at,
            r.finished_at,
            r.duration_minutes,
            r.final_cost,
            r.status,
            NOW()
        FROM ods.rentals r
        JOIN dds.dim_users du ON r.user_id = du.user_id AND du.is_current = TRUE
        JOIN dds.dim_stations ds ON r.station_id = ds.station_id
        LEFT JOIN dds.dim_tariff dt ON r.tariff_version = dt.tariff_version
        ON CONFLICT (rental_id) DO UPDATE SET
            finished_at = EXCLUDED.finished_at,
            end_date_id = EXCLUDED.end_date_id,
            end_time_id = EXCLUDED.end_time_id,
            duration_minutes = EXCLUDED.duration_minutes,
            final_cost = EXCLUDED.final_cost,
            status = EXCLUDED.status,
            dw_updated_at = NOW();
        """, 
        do_xcom_push=False
    )

    [load_dim_users, load_dim_stations] >> load_fact_rentals