import pendulum
from airflow.sdk import dag, task
from ingestion import recruitee, recruitee_loader, checks, alerts
from datetime import timedelta

@dag(
    schedule="30 4 * * *", 
    catchup=False,
    start_date=pendulum.datetime(2026,9,27,tz="UTC"),
    default_args={
        "retries": 2,
        "on_failure_callback": alerts.alert_on_failure,
        "retry_delay": timedelta(minutes=5),
        # ~1,470 boards, 3.5x Ashby's 424 (which took ~13 min per task). Sized from that,
        # with room to spare; re-measure after the first full run and tighten.
        "execution_timeout": timedelta(minutes=120),
    }
)
def recruitee_ingestion():

    @task
    def extract(ds=None):
        # Returning a value pushes it to XCom, so the check task can read it.
        return recruitee.date_run(ds)

    @task
    def load(ds=None):
        # Returning a value pushes it to XCom, so the check task can read it.
        return recruitee_loader.date_run(ds)

    @task(retries=0)
    def check(load_summary, extract_summary, ds=None):
        checks.run_checks("recruitee", ds, summary=load_summary,
                                     extract_summary=extract_summary)

    extract_task = extract()
    load_task = load()
    extract_task >> load_task        # ordering only: load reads GCS, not the summary
    # Passing the values also creates load -> check and extract -> check. By keyword: two
    # dicts of similar shape are easy to swap positionally, and nothing would complain.
    check(load_summary=load_task, extract_summary=extract_task)

recruitee_ingestion()