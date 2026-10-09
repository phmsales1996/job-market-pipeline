import pendulum
from airflow.sdk import dag, task
from ingestion import lever, lever_loader, checks, alerts
from ingestion.assets import INGESTION_FINISHED
from datetime import timedelta

@dag(
    schedule="30 2 * * *", 
    catchup=False,
    start_date=pendulum.datetime(2026,9,27,tz="UTC"),
    default_args={
        "retries": 2,
        "on_failure_callback": alerts.alert_on_failure,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=45),
    }
)
def lever_ingestion():

    @task
    def extract(ds=None):
        # Returning a value pushes it to XCom, so the check task can read it.
        return lever.date_run(ds)

    @task
    def load(ds=None):
        # Returning a value pushes it to XCom, so the check task can read it.
        return lever_loader.date_run(ds)

    @task(retries=0)
    def check(load_summary, extract_summary, ds=None):
        checks.run_checks("lever", ds, summary=load_summary,
                                     extract_summary=extract_summary)

    @task(outlets=[INGESTION_FINISHED["lever"]])
    def finished():
        """Announces that tonight's Lever run is over, whether or not it succeeded."""

    extract_task = extract()
    load_task = load()
    extract_task >> load_task        # ordering only: load reads GCS, not the summary
    # Passing the values also creates load -> check and extract -> check. By keyword: two
    # dicts of similar shape are easy to swap positionally, and nothing would complain.
    check_task = check(load_summary=load_task, extract_summary=extract_task)

    check_task >> finished().as_teardown()
lever_ingestion()