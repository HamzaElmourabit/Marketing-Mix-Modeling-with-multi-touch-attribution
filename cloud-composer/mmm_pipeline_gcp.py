"""
Cloud Composer optimized DAG for MMM Pipeline
Uses PythonOperator and integrates with BigQuery natively
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryCheckOperator
from google.cloud import bigquery
import os
import subprocess

default_args = {
    'owner': 'mmm-team',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT', 'rh-etl-project-467521')
DATASET = os.environ.get('BIGQUERY_DATASET', 'MMM_datset')
TABLE = os.environ.get('BIGQUERY_TABLE', 'mmm')
REPO_DIR = '/home/airflow/gcs/data/mmm_repo'  # Cloud Composer default path


def run_etl_task(**context):
    """Execute ETL pipeline and load to BigQuery"""
    print(f"Running ETL from {REPO_DIR}")
    result = subprocess.run(
        [f'cd {REPO_DIR} && python run_pipeline.py --bigquery'],
        shell=True,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"ETL failed: {result.stderr}")
    print(result.stdout)


def run_tests_task(**context):
    """Run pytest suite"""
    print(f"Running tests from {REPO_DIR}")
    result = subprocess.run(
        [f'cd {REPO_DIR} && python -m pytest -q'],
        shell=True,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Tests failed: {result.stderr}")
    print(result.stdout)


def train_model_task(**context):
    """Train MMM model"""
    print(f"Training model from {REPO_DIR}")
    result = subprocess.run(
        [f'cd {REPO_DIR} && python scripts/train_model.py'],
        shell=True,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Model training failed: {result.stderr}")
    print(result.stdout)


def check_bigquery_data(**context):
    """Verify BigQuery table has data"""
    client = bigquery.Client(project=PROJECT_ID)
    query = f"SELECT COUNT(*) as row_count FROM `{PROJECT_ID}.{DATASET}.{TABLE}`"
    result = client.query(query).result()
    row_count = list(result)[0][0]
    print(f"BigQuery table has {row_count} rows")
    if row_count == 0:
        raise RuntimeError("BigQuery table is empty after ETL")


with DAG(
    dag_id='mmm_pipeline_gcp',
    default_args=default_args,
    description='MMM Pipeline on Cloud Composer with BigQuery',
    schedule_interval='0 2 * * *',  # Daily at 2 AM UTC
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['mmm', 'gcp', 'bigquery'],
) as dag:

    run_etl = PythonOperator(
        task_id='run_etl',
        python_callable=run_etl_task,
        provide_context=True,
    )

    check_data = BigQueryCheckOperator(
        task_id='check_bigquery_data',
        sql=f"SELECT COUNT(*) FROM `{PROJECT_ID}.{DATASET}.{TABLE}`",
        use_legacy_sql=False,
    )

    run_tests = PythonOperator(
        task_id='run_tests',
        python_callable=run_tests_task,
        provide_context=True,
    )

    train_model = PythonOperator(
        task_id='train_model',
        python_callable=train_model_task,
        provide_context=True,
    )

    run_etl >> check_data >> run_tests >> train_model
