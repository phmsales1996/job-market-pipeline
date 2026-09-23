import pendulum
from airflow.sdk import dag, task
from ingestion import greenhouse, greenhouse_loader, greenhouse_checks, alerts
from datetime import timedelta

@dag(
    schedule="30 1 * * *", 
    catchup=False,
    start_date=pendulum.datetime(2026,9,22,tz="UTC"),
    default_args={
        "retries": 2,
        "on_failure_callback": alerts.alert_on_failure,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=20),
    }
)
def greenhouse_ingestion():

    @task
    def extract(ds=None):
        greenhouse.date_run(ds)
    
    @task
    def load(ds=None):
        greenhouse_loader.date_run(ds)

    @task(retries=0)
    def check(ds=None):
        greenhouse_checks.run_checks(ds)
    
    extract() >> load() >> check()

greenhouse_ingestion()