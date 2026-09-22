import pendulum
from airflow.sdk import dag, task
from ingestion import greenhouse, greenhouse_loader

@dag(
    schedule="30 1 * * *", 
    catchup=False,
    start_date=pendulum.datetime(2026,9,22,tz="UTC")
)
def greenhouse_ingestion():

    @task
    def extract(ds=None):
        greenhouse.date_run(ds)
    
    @task
    def load(ds=None):
        greenhouse_loader.date_run(ds)
    
    extract() >> load()

greenhouse_ingestion()