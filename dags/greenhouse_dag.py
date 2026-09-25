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
        # ~3.4s per company to extract and ~5s per file to load, measured at 51
        # companies: roughly 12 and 17 minutes at 200+. 45 gives headroom for a slow day.
        "execution_timeout": timedelta(minutes=45),
    }
)
def greenhouse_ingestion():

    @task
    def extract(ds=None):
        greenhouse.date_run(ds)
    
    @task
    def load(ds=None):
        # Returning a value pushes it to XCom, so the check task can read it.
        return greenhouse_loader.date_run(ds)

    @task(retries=0)
    def check(load_summary, ds=None):
        greenhouse_checks.run_checks(ds, summary=load_summary)

    extract_task = extract()
    load_task = load()
    extract_task >> load_task        # ordering only: extract passes nothing to load
    check(load_task)                 # passing the value also creates load -> check

greenhouse_ingestion()