import datetime
import logging
import json
import pathlib
import os
# google.cloud is a namespace package (storage and bigquery ship as separate
# distributions into one folder), which mypy cannot follow statically - hence the
# narrow ignore. Keep the [attr-defined] code: a bare ignore would also hide typos
# like bigquery.LoadJobConsfig.
from google.cloud import storage, bigquery  # type: ignore[attr-defined]
from ingestion.dates import require_date
from google.api_core.exceptions import BadRequest
from typing import Any
from collections.abc import Callable

logger = logging.getLogger(__name__)

bucket_name = os.environ['NAME_BUCKET']

dataset = os.environ['NAME_DATASET']

# Rows per load job. Bigger = fewer, slower load jobs and more memory in flight;
# smaller = more jobs, each paying a few seconds of startup. Measured at ~170 KiB of
# peak memory per row in a batch (each row carries `content` and `raw`, and
# load_table_from_json serialises the batch again before sending), so 2k rows is
# roughly 350 MiB - comfortable on a host shared with other services.
BATCH_ROWS = int(os.environ.get("LOADER_BATCH_ROWS", "2000"))


def fetch_raw_json(path: str) -> bytes:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(path)
    saved = blob.download_as_bytes()
    return saved
 
def load_rows(source: str, rows: list, write_disposition: str = "WRITE_APPEND") -> None:
    table_id = f"{dataset}.{source}_postings_incoming"
    client = bigquery.Client()
    job_config = bigquery.LoadJobConfig(write_disposition=write_disposition, autodetect=False)
    job = client.load_table_from_json(rows, table_id, job_config=job_config)
    try:
        job.result()
    except BadRequest:
        for error in (job.errors or [])[:5]:
            logger.error(f"Load error: {error}")
        raise

def truncate_staging(source: str) -> None:
    table_id = f"{dataset}.{source}_postings_incoming"
    client = bigquery.Client()
    client.query(f"TRUNCATE TABLE `{table_id}`").result()

def fetch_files(prefix_given: str):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=prefix_given)
    blobs_list = list(blobs)
    # One line per file was fine at 5 companies and is 212 lines of noise at scale;
    # the names are in GCS if anyone needs them.
    logger.info(f"Found {len(blobs_list)} landed files under {prefix_given}")
    logger.debug("landed files: " + ", ".join(b.name for b in blobs_list))
    return blobs_list

def run_merge(source: str):
    sql_path = pathlib.Path(__file__).parent.parent / "sql" / f"merge_{source}_postings.sql"
    sql_text = sql_path.read_text()
    client = bigquery.Client()
    result = client.query(sql_text.format(dataset=dataset)).result()
    return result

def run_load(source: str, parse_fn: Callable[[bytes], list[dict]], date: str) -> dict:
    require_date(date)
    prefix_given = f"{source}/ingest_date={date}/"
    files = fetch_files(prefix_given)

    # Rows are accumulated across files and flushed in batches, which bounds two things
    # at once: memory (a batch plus one file being parsed, not the whole day) and the
    # number of load jobs (each costs a few seconds of fixed overhead regardless of size).
    # Staging is emptied once up front, so every load below is an append.
    truncate_staging(source)
    batch: list[dict] = []
    files_read = 0
    rows_loaded = 0
    load_jobs = 0
    files_with_rows = 0
    for n, file in enumerate(files, 1):
        rows = parse_fn(fetch_raw_json(file.name))
        files_read += 1
        if rows:
            files_with_rows += 1
        # The three timestamps belong to the pipeline, not to the source, so they are
        # stamped here: one format, one place, identical for every ATS.
        landed_at = file.time_created.isoformat()
        company = slug_from_path(file.name)
        for row in rows:
            row["landed_at"] = landed_at
            row["first_seen_at"] = landed_at
            row["last_seen_at"] = landed_at
            row["company_slug"] = company
        batch.extend(rows)
        if len(batch) >= BATCH_ROWS:
            load_rows(source, batch, write_disposition="WRITE_APPEND")
            rows_loaded += len(batch)
            load_jobs += 1
            batch = []
        # A 200-file run is otherwise silent for ten minutes: say where it is.
        if n % 10 == 0 or n == len(files):
            logger.info(f"{n}/{len(files)} files read, {rows_loaded + len(batch)} rows so far")
    if batch:
        load_rows(source, batch, write_disposition="WRITE_APPEND")
        rows_loaded += len(batch)
        load_jobs += 1
    logger.info(
        f"Loaded {rows_loaded} rows into staging for {date} "
        f"from {len(files)} files in {load_jobs} load jobs"
    )
    run_merge(source)
    logger.info(f"Merged staging into the final table for {date}")
    return {"date": date, "source": source, "files_read": files_read,
            "files_with_rows": files_with_rows, "rows_loaded": rows_loaded,
            "load_jobs": load_jobs}

def slug_from_path(path: str) -> str:
    """The company slug from a landed file's path: <source>/ingest_date=<date>/<slug>/<time>.<ext>.

    The path is the only place the slug survives: most sources do not repeat the company
    inside each posting, so without this a loaded row cannot say which board it came from.
    """
    return path.split("/")[2]