from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'dwh_team',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'raw_data_ingestion',
    default_args=default_args,
    description='Extract data from operational DBs to RAW layer',
    schedule_interval='*/10 * * * *',
    catchup=False,
    max_active_runs=1,
)


load_users_task = PostgresOperator(
    task_id='load_to_raw_users',
    postgres_conn_id='dwh_postgres',
    sql="""
        INSERT INTO raw.users (user_id, email, phone, status, created_at, loaded_at, source_system)
        SELECT user_id, email, phone, status, created_at, NOW(), 'user_service'
        FROM staging.temp_users_staging
        ON CONFLICT (user_id) DO NOTHING;
    """,
    dag=dag,
)


load_offers_shard_0 = PostgresOperator(
    task_id='load_offers_shard_0',
    postgres_conn_id='offer_service_shard_0',
    sql="""
        INSERT INTO raw.offers (offer_id, user_id, station_id, tariff_snapshot, created_at, expires_at, status, tariff_version, shard_id, loaded_at, source_system)
        SELECT offer_id, user_id, station_id, tariff_snapshot, created_at, expires_at, status, tariff_version, 0, NOW(), 'offer_service'
        FROM offers
        WHERE created_at > COALESCE(
            (SELECT MAX(created_at) FROM raw.offers WHERE shard_id = 0), 
            '1970-01-01'::timestamp
        );
    """,
    dag=dag,
)


load_offers_shard_1 = PostgresOperator(
    task_id='load_offers_shard_1',
    postgres_conn_id='offer_service_shard_1',
    sql="""
        INSERT INTO raw.offers (offer_id, user_id, station_id, tariff_snapshot, created_at, expires_at, status, tariff_version, shard_id, loaded_at, source_system)
        SELECT offer_id, user_id, station_id, tariff_snapshot, created_at, expires_at, status, tariff_version, 1, NOW(), 'offer_service'
        FROM offers
        WHERE created_at > COALESCE(
            (SELECT MAX(created_at) FROM raw.offers WHERE shard_id = 1), 
            '1970-01-01'::timestamp
        );
    """,
    dag=dag,
)

load_rentals_shard_0 = PostgresOperator(
    task_id='load_rentals_shard_0',
    postgres_conn_id='rental_service_shard_0',
    sql="""
        INSERT INTO raw.rentals (
            rental_id, offer_id, user_id, station_id, started_at, finished_at, 
            status, tariff_snapshot, tariff_version, final_cost, loaded_at, source_system
        )
        SELECT rental_id, offer_id, user_id, station_id, started_at, finished_at, 
               status, tariff_snapshot, tariff_version, final_cost, NOW(), 'rental_service'
        FROM staging.temp_rentals_shard_0;
    """,
    dag=dag,
)


load_rentals_shard_1 = PostgresOperator(
    task_id='load_rentals_shard_1',
    postgres_conn_id='rental_service_shard_1',
    sql="""
        INSERT INTO raw.rentals (
            rental_id, offer_id, user_id, station_id, started_at, finished_at, 
            status, tariff_snapshot, tariff_version, final_cost, loaded_at, source_system
        )
        SELECT rental_id, offer_id, user_id, station_id, started_at, finished_at, 
               status, tariff_snapshot, tariff_version, final_cost, NOW(), 'rental_service'
        FROM staging.temp_rentals_shard_1;
    """,
    dag=dag,
)


load_rental_events = PostgresOperator(
    task_id='load_rental_events',
    postgres_conn_id='rental_service',
    sql="""
        INSERT INTO raw.rental_events (event_id, rental_id, ts, event_type, payload, loaded_at)
        SELECT event_id, rental_id, ts, event_type, payload, NOW()
        FROM staging.temp_rental_events_staging
        ON CONFLICT (event_id) DO NOTHING;
    """,
    dag=dag,
)


load_offer_audit = PostgresOperator(
    task_id='load_offer_audit',
    postgres_conn_id='offer_service',
    sql="""
        INSERT INTO raw.offer_audit (id, offer_id, event_type, ts, payload_json, loaded_at)
        SELECT id, offer_id, event_type, ts, payload_json, NOW()
        FROM staging.temp_offer_audit_staging
        ON CONFLICT (id) DO NOTHING;
    """,
    dag=dag,
)


load_users_task >> [load_offers_shard_0, load_offers_shard_1]
[load_offers_shard_0, load_offers_shard_1] >> [load_rentals_shard_0, load_rentals_shard_1]
[load_rentals_shard_0, load_rentals_shard_1] >> load_rental_events
[load_offers_shard_0, load_offers_shard_1] >> load_offer_audit
