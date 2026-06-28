from datetime import datetime, timedelta
import os
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'mmm-team',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

REPO_DIR = os.environ.get('REPO_DIR', '/workspace')
MLFLOW_EXPERIMENT = os.environ.get('MLFLOW_EXPERIMENT_NAME', 'MMM-Orchestrated')
MLFLOW_TRACKING_URI = os.environ.get('MLFLOW_TRACKING_URI', f"sqlite:///{os.path.join(REPO_DIR, 'mlflow.db')}")

with DAG(
    dag_id='mmm_pipeline',
    default_args=default_args,
    description='Orchestrates ETL, tests and model training for MMM project',
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:

    run_etl = BashOperator(
        task_id='run_etl',
        bash_command=f'cd {REPO_DIR} && python run_pipeline.py --bigquery',
    )

    run_tests = BashOperator(
        task_id='run_tests',
        bash_command=f'cd {REPO_DIR} && python -m pytest -q',
    )

    train_model = BashOperator(
        task_id='train_model',
        bash_command=f'cd {REPO_DIR} && python scripts/train_model.py',
        env={
            'MLFLOW_EXPERIMENT_NAME': MLFLOW_EXPERIMENT,
            'MLFLOW_TRACKING_URI': MLFLOW_TRACKING_URI,
            'ENABLE_BAYESIAN_TRACKING': '1',
            'ENABLE_GEO_TRACKING': '1',
        },
    )

    run_etl >> run_tests >> train_model
