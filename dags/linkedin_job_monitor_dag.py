"""
Airflow DAG: LinkedIn Senior Data Engineer job monitor.

Runs every hour and alerts when new jobs are posted matching:
  - Remote Senior Data Engineer roles in India
  - Similar roles in Kochi and Trivandrum (Thiruvananthapuram)

Configure alerts via environment variables (see job_monitor/config.py).
"""

import os
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python_operator import PythonOperator

# Allow importing job_monitor from the repo root
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from job_monitor.monitor import run_monitor  # noqa: E402

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2026, 7, 3),
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "linkedin_senior_data_engineer_monitor",
    default_args=default_args,
    description="Hourly LinkedIn job alerts for Senior Data Engineer roles",
    schedule_interval=timedelta(hours=1),
    catchup=False,
    max_active_runs=1,
    tags=["linkedin", "jobs", "monitoring"],
)

check_linkedin_jobs = PythonOperator(
    task_id="check_linkedin_jobs",
    python_callable=run_monitor,
    dag=dag,
)
