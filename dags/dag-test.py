from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.operators.dummy import DummyOperator
from datetime import datetime

with DAG('test_dag', start_date=datetime(2025,1,1), schedule_interval=None, catchup=False) as dag:
    DummyOperator(task_id='start')
    test_insert = PostgresOperator(
        task_id='test_insert',
        postgres_conn_id='dwh_postgres',
        sql="""INSERT INTO raw.offers 
        (offer_id, user_id, station_id, tariff_snapshot, created_at, expires_at, status, tariff_version,
         shard_id, loaded_at, source_system) 
         VALUES ('22222222-2222-2222-2222-222222222222', '11111111-1111-1111-1111-111111111111', 
         'station-001', '{}', NOW(), NOW(), 'active', 1, 0, NOW(), 'test');""",
        do_xcom_push=False
    )