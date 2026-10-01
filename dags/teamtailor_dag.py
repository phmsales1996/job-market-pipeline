import pendulum
from airflow.sdk import dag, task
from ingestion import teamtailor, teamtailor_loader, checks, alerts
from datetime import timedelta

@dag(
    schedule="30 5 * * *", 
    catchup=False,
    start_date=pendulum.datetime(2026,9,27,tz="UTC"),
    default_args={
        "retries": 2,
        "on_failure_callback": alerts.alert_on_failure,
        "retry_delay": timedelta(minutes=5),
        # ~1,000 boards, one request each like Recruitee (1,471 boards: extract 40 min, load
        # 34 min). Scaled from that with room to spare; tighten after the first full run.
        "execution_timeout": timedelta(minutes=90),
    }
)
def teamtailor_ingestion():

    @task
    def extract(ds=None):
        # Returning a value pushes it to XCom, so the check task can read it.
        return teamtailor.date_run(ds)

    @task
    def load(ds=None):
        # Returning a value pushes it to XCom, so the check task can read it.
        return teamtailor_loader.date_run(ds)

    @task(retries=0)
    def check(load_summary, extract_summary, ds=None):
        checks.run_checks("teamtailor", ds, summary=load_summary,
                                     extract_summary=extract_summary)

    extract_task = extract()
    load_task = load()
    extract_task >> load_task        # ordering only: load reads GCS, not the summary
    # Passing the values also creates load -> check and extract -> check. By keyword: two
    # dicts of similar shape are easy to swap positionally, and nothing would complain.
    check(load_summary=load_task, extract_summary=extract_task)

teamtailor_ingestion()