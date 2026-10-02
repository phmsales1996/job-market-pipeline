import pendulum
from airflow.sdk import dag, task
from ingestion import workable, workable_loader, checks, alerts
from datetime import timedelta

@dag(
    schedule="30 6 * * *", 
    catchup=False,
    start_date=pendulum.datetime(2026,9,27,tz="UTC"),
    default_args={
        "retries": 2,
        "on_failure_callback": alerts.alert_on_failure,
        "retry_delay": timedelta(minutes=5),
        # ~1,000 boards (list request each) plus up to MAX_DETAILS_PER_RUN (3,000) detail
        # requests at ~0.4 s: ~8 + ~20 min extract. Load ~30k rows. Tighten after real runs.
        "execution_timeout": timedelta(minutes=90),
    }
)
def workable_ingestion():

    @task
    def extract(ds=None):
        # Returning a value pushes it to XCom, so the check task can read it.
        return workable.date_run(ds)

    @task
    def load(ds=None):
        # Returning a value pushes it to XCom, so the check task can read it.
        return workable_loader.date_run(ds)

    @task(retries=0)
    def check(load_summary, extract_summary, ds=None):
        checks.run_checks("workable", ds, summary=load_summary,
                                     extract_summary=extract_summary)

    extract_task = extract()
    load_task = load()
    extract_task >> load_task        # ordering only: load reads GCS, not the summary
    # Passing the values also creates load -> check and extract -> check. By keyword: two
    # dicts of similar shape are easy to swap positionally, and nothing would complain.
    check(load_summary=load_task, extract_summary=extract_task)

workable_ingestion()