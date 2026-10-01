import logging
import datetime
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from google.cloud import storage, bigquery  # type: ignore[attr-defined]
from ingestion.dates import require_date
from collections.abc import Callable

logger = logging.getLogger(__name__)

bucket_name = os.environ['NAME_BUCKET']
dataset = os.environ['NAME_DATASET']

# One session for the whole run: it reuses the TCP/TLS connection across companies, and
# retries the failures worth retrying. 404 (board gone) and 401/403 are not in
# status_forcelist, so they fail immediately instead of burning three attempts.
_retry = Retry(
    total=3,
    backoff_factor=1,                              # waits ~1s, 2s, 4s between attempts
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
    respect_retry_after_header=True,               # a 429 usually says how long to wait
)
session = requests.Session()
session.mount("https://", HTTPAdapter(max_retries=_retry))

CONTENT_TYPES = {"json": "application/json", "xml": "application/xml"}

def land_raw(date: str, content: bytes, source: str, slug: str, file_format: str="json") -> str:
    timestamp = datetime.datetime.now().strftime("%H%M%S")
    destination_path = f"{source}/ingest_date={date}/{slug}/{timestamp}.{file_format}"

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_path)
    blob.upload_from_string(content, content_type=CONTENT_TYPES[file_format])

    return destination_path

def fetch_companies(ats: str) -> list:
    client = bigquery.Client()
    query = f"SELECT name, external_id FROM `{dataset}.companies` WHERE ats = @ats ORDER BY external_id ASC"
    config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("ats", "STRING", ats)]
    )
    results = client.query(query, job_config=config).result()
    results_list = list(results)
    return results_list

def run_extract(ats: str, fetch_fn: Callable[[str], bytes | None], date: str, file_format: str = "json") -> dict:
    require_date(date)
    companies = fetch_companies(ats)
    if not companies:
        raise ValueError(f"No companies found in the registry for ats='{ats}' ({date}).")

    failures = []
    total = len(companies)
    for i, company in enumerate(companies, 1):
        slug = company.external_id
        raw = fetch_fn(slug)
        if raw is not None:
            logger.info(f"[{i}/{total}] Fetched {len(raw)} bytes for {slug}")
            path = land_raw(date, raw, source=ats, slug=slug, file_format=file_format)
            logger.info(f"Landed to gs://{bucket_name}/{path}")
        else:
            failures.append(slug)
            logger.error(f"[{i}/{total}] No data landed for {slug} ({date})")

    logger.info(f"Extracted {total - len(failures)}/{total} companies for {date}")
    if failures:
        logger.warning(f"Failed companies for {date}: {', '.join(sorted(failures))}")
    s = summarise_extract(ats, date, total, failures)
    logger.info(s)
    return s
    

def summarise_extract(ats: str, date: str, total: int, failures: list) -> dict:
    succeeded = total - len(failures)
    if total > 0 and len(failures) == total:
       raise ValueError(
            f"All {total} companies failed for {date}: {', '.join(sorted(failures))}"
        )
    return {"date": date, "companies": total, "succeeded": succeeded, "failed": len(failures),
            "failed_slugs": sorted(failures), "ats": ats}