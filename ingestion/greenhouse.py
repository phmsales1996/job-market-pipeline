import requests
import logging
import datetime
import os
#import argparse
from google.cloud import storage, bigquery
from ingestion.dates import require_date

logger = logging.getLogger(__name__)

bucket_name = os.environ['NAME_BUCKET']
dataset = os.environ['NAME_DATASET']

"""
parser = argparse.ArgumentParser()
parser.add_argument("slug")
args = parser.parse_args()
"""

def fetch_greenhouse_raw(slug: str) -> bytes:
    try:    
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logger.error(f"Fetch failed for {slug}: {e}")
        return None
        

def land_raw_json(date: str, content: bytes, source: str, slug: str) -> str:
    timestamp = datetime.datetime.now().strftime("%H%M%S")
    destination_path = f"{source}/ingest_date={date}/{slug}/{timestamp}.json"

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_path)
    blob.upload_from_string(content, content_type="application/json")

    return destination_path

def fetch_companies() -> list:
    client = bigquery.Client()
    query = f"SELECT * FROM `{dataset}.companies` WHERE ats = 'greenhouse'"
    results = client.query(query).result()
    results_list = list(results)
    for row in results_list:
        logger.info(f"Company in registry: {row.name}")
    return results_list

def date_run(date: str):
    require_date(date)
    companies = fetch_companies()
    if not companies:
        raise ValueError(f"No companies found in the registry for ats='greenhouse' ({date}).")

    failures = []
    for company in companies:
        slug = company.external_id
        raw = fetch_greenhouse_raw(slug)
        if raw is not None:
            logger.info(f"Fetched {len(raw)} bytes for {slug}")
            path = land_raw_json(date, raw, source="greenhouse", slug=slug)
            logger.info(f"Landed to gs://{bucket_name}/{path}")
        else:
            failures.append(slug)
            logger.error(f"No data landed for {slug} ({date})")

    logger.info(f"Extracted {len(companies) - len(failures)}/{len(companies)} companies for {date}")
    if failures:
        logger.warning(f"Failed companies for {date}: {', '.join(sorted(failures))}")
    if len(failures) == len(companies):
        raise ValueError(
            f"All {len(companies)} companies failed for {date}: {', '.join(sorted(failures))}"
        )
    


if __name__ == "__main__":
    import sys
    import datetime
    # Only when run as a script: Airflow configures logging itself.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    date_run(date)
    

    