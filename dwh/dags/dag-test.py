from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'dwh_team',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def dummy_task():
    print("DAG is working!")

with DAG(
    dag_id='raw_data_ingestion',
    description='Extract data from operational DBs to RAW layer',
    schedule_interval='*/10 * * * *',
    default_args=default_args,
    catchup=False,
    max_active_runs=1,
) as dag:

    test_task = PythonOperator(
        task_id='test_task',
        python_callable=dummy_task
    )

    load_users_task = PostgresOperator(
        task_id='load_to_raw_users',
        postgres_conn_id='DWH_POSTGRES',
        sql="""
            INSERT INTO raw.users (user_id, email, phone, status, created_at, loaded_at, source_system)
            SELECT user_id, email, phone, status, created_at, NOW(), 'user_service'
            FROM staging.temp_users_staging
            ON CONFLICT (user_id) DO NOTHING;
        """
    )

    load_offers_shard_0 = PostgresOperator(
        task_id='load_offers_shard_0',
        postgres_conn_id='OFFER_SERVICE_SHARD_0',
        sql="""
            INSERT INTO raw.offers (offer_id, user_id, station_id, tariff_snapshot, created_at, expires_at, status, tariff_version, shard_id, loaded_at, source_system)
            SELECT offer_id, user_id, station_id, tariff_snapshot, created_at, expires_at, status, tariff_version, 0, NOW(), 'offer_service'
            FROM offers;
        """
    )

    load_offers_shard_1 = PostgresOperator(
        task_id='load_offers_shard_1',
        postgres_conn_id='OFFER_SERVICE_SHARD_1',
        sql="""
            INSERT INTO raw.offers (offer_id, user_id, station_id, tariff_snapshot, created_at, expires_at, status, tariff_version, shard_id, loaded_at, source_system)
            SELECT offer_id, user_id, station_id, tariff_snapshot, created_at, expires_at, status, tariff_version, 1, NOW(), 'offer_service'
            FROM offers;
        """
    )

    test_task >> load_users_task >> [load_offers_shard_0, load_offers_shard_1]
