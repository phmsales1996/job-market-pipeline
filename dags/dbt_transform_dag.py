import pendulum
from airflow.sdk import dag, task
from ingestion import alerts
from ingestion.assets import INGESTION_FINISHED
from datetime import timedelta

@dag(
    schedule=list(INGESTION_FINISHED.values()),
    catchup=False,
    start_date=pendulum.datetime(2026,9,27,tz="UTC"),
    default_args={
        "retries": 0,
        "on_failure_callback": alerts.alert_on_failure,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=45),
    }
)
def dbt_transform():
    @task.bash
    def dbt_build():
         return "dbt build"

    dbt_build()

dbt_transform()