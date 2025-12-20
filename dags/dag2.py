from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator
from datetime import datetime

with DAG(
    'transform_raw_to_ods',
    default_args={'owner': 'dwh_team'},
    description='Transform RAW → ODS layer',
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
) as dag:

    transform_users = PostgresOperator(
        task_id='transform_raw_to_ods_users',
        postgres_conn_id='dwh_postgres',
        sql="""
        INSERT INTO ods.users (user_id, email, phone, status, created_at, updated_at, dw_loaded_at)
        SELECT user_id, email, phone, status, created_at, NOW(), NOW()
        FROM (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY loaded_at DESC) AS rn
            FROM raw.users
        ) t
        WHERE rn = 1
        ON CONFLICT (user_id) DO UPDATE SET
            email = EXCLUDED.email,
            phone = EXCLUDED.phone,
            status = EXCLUDED.status,
            updated_at = EXCLUDED.updated_at;
        """,
        do_xcom_push=False
    )

    transform_offers = PostgresOperator(
        task_id='transform_raw_to_ods_offers',
        postgres_conn_id='dwh_postgres',
        sql="""
        INSERT INTO ods.offers (offer_id, user_id, station_id, tariff_snapshot, created_at, expires_at, status, tariff_version, shard_id, loaded_at, source_system, updated_at, dw_loaded_at)
        SELECT offer_id, user_id, station_id, tariff_snapshot, created_at, expires_at, status, tariff_version, shard_id, loaded_at, source_system, NOW(), NOW()
        FROM (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY offer_id ORDER BY loaded_at DESC) AS rn
            FROM raw.offers
        ) t
        WHERE rn = 1
        ON CONFLICT (offer_id) DO NOTHING;
        """,
        do_xcom_push=False
    )

    transform_rentals = PostgresOperator(
        task_id='transform_raw_to_ods_rentals',
        postgres_conn_id='dwh_postgres',
        sql="""
        INSERT INTO ods.rentals (rental_id, offer_id, user_id, station_id, started_at, finished_at, status, tariff_snapshot, tariff_version, final_cost, duration_minutes, updated_at, dw_loaded_at)
        SELECT
            rental_id,
            offer_id,
            user_id,
            station_id,
            started_at,
            finished_at,
            status,
            tariff_snapshot,
            tariff_version,
            final_cost,
            CASE
                WHEN finished_at IS NOT NULL
                THEN EXTRACT(EPOCH FROM (finished_at - started_at)) / 60
                ELSE NULL
            END::INTEGER,
            NOW(),
            NOW()
        FROM (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY rental_id ORDER BY loaded_at DESC) AS rn
            FROM raw.rentals
        ) t
        WHERE rn = 1
        ON CONFLICT (rental_id) DO UPDATE SET
            finished_at = EXCLUDED.finished_at,
            status = EXCLUDED.status,
            duration_minutes = EXCLUDED.duration_minutes,
            updated_at = EXCLUDED.updated_at;
        """,
        do_xcom_push=False
    )

    [transform_users, transform_offers, transform_rentals]