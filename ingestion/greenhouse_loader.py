import datetime
import logging
import json
import pathlib
import os
from google.cloud import storage, bigquery
from ingestion.dates import require_date

logger = logging.getLogger(__name__)

bucket_name = os.environ['NAME_BUCKET']

dataset = os.environ['NAME_DATASET']

table_id = dataset+".greenhouse_postings_incoming"

# Rows per load job. Bigger = fewer, slower load jobs and more memory in flight;
# smaller = more jobs, each paying a few seconds of startup. Measured at ~170 KiB of
# peak memory per row in a batch (each row carries `content` and `raw`, and
# load_table_from_json serialises the batch again before sending), so 2k rows is
# roughly 350 MiB - comfortable on a host shared with other services.
BATCH_ROWS = int(os.environ.get("LOADER_BATCH_ROWS", "2000"))

sql_path = pathlib.Path(__file__).parent.parent / "sql" / "merge_greenhouse_postings.sql"
sql_text = sql_path.read_text()

def first_field(items: list, key: str):
    if items:
        return items[0][key]
    else:
        return None

def fetch_raw_json(path: str) -> bytes:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(path)
    saved = blob.download_as_bytes()
    return saved
 
def transform(job: dict, landed_at: datetime.datetime) -> dict:
    transformed_job = {}
    transformed_job["id"] = job["id"]
    transformed_job["title"] = job["title"]
    transformed_job["url"] = job["absolute_url"]
    transformed_job["location"] = job["location"]["name"]
    transformed_job["company"] = job["company_name"]
    transformed_job["language"] = job["language"]
    transformed_job["content"] = job["content"]
    transformed_job["updated_at"] = job["updated_at"]
    transformed_job["published_at"] = job["first_published"]
    transformed_job["deadline_at"] = job["application_deadline"]
    transformed_job["raw"] = json.dumps(job)
    transformed_job["first_seen_at"] = landed_at.isoformat()
    transformed_job["last_seen_at"] = landed_at.isoformat()
    transformed_job["department"] = first_field(job["departments"], "name")
    transformed_job["office"] = first_field(job["offices"], "location")
    transformed_job['landed_at'] = landed_at.isoformat()

    return transformed_job

def load_rows(rows: list, write_disposition: str = "WRITE_APPEND") -> None:
    client = bigquery.Client()
    job_config = bigquery.LoadJobConfig(write_disposition=write_disposition, autodetect=False)
    job = client.load_table_from_json(rows, table_id, job_config=job_config)
    return job.result()

def truncate_staging() -> None:
    client = bigquery.Client()
    client.query(f"TRUNCATE TABLE `{table_id}`").result()

def fetch_files(prefix_given: str):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=prefix_given)
    blobs_list = list(blobs)
    for blob in blobs_list:
        logger.info(f"Found landed file: {blob.name}")
    return blobs_list

def run_merge():
    client = bigquery.Client()
    result = client.query(sql_text.format(dataset=dataset)).result()
    return result

def date_run(date: str):
    require_date(date)
    prefix_given = "greenhouse/ingest_date="+date+"/"
    files = fetch_files(prefix_given)

    # Rows are accumulated across files and flushed in batches, which bounds two things
    # at once: memory (a batch plus one file being parsed, not the whole day) and the
    # number of load jobs (each costs a few seconds of fixed overhead regardless of size).
    # Staging is emptied once up front, so every load below is an append.
    truncate_staging()
    batch = []
    rows_loaded = 0
    load_jobs = 0
    for file in files:
        data = json.loads(fetch_raw_json(file.name))
        batch.extend(transform(job, file.time_created) for job in data["jobs"])
        if len(batch) >= BATCH_ROWS:
            load_rows(batch, write_disposition="WRITE_APPEND")
            rows_loaded += len(batch)
            load_jobs += 1
            batch = []
    if batch:
        load_rows(batch, write_disposition="WRITE_APPEND")
        rows_loaded += len(batch)
        load_jobs += 1
    logger.info(
        f"Loaded {rows_loaded} rows into staging for {date} "
        f"from {len(files)} files in {load_jobs} load jobs"
    )
    run_merge()
    logger.info(f"Merged staging into the final table for {date}")


if __name__ == "__main__":
    import sys
    import datetime
    # Only when run as a script: Airflow configures logging itself.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    date_run(date)
