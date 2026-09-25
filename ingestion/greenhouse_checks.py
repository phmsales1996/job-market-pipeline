import os
import logging
from google.cloud import storage, bigquery
from ingestion import greenhouse
from ingestion.dates import require_date

logger = logging.getLogger(__name__)

bucket_name = os.environ['NAME_BUCKET']
dataset = os.environ['NAME_DATASET']

def files_per_company(date:str):
    prefix_given = "greenhouse/ingest_date="+date+"/"
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=prefix_given)
    blobs_list = list(blobs)
    result = {}
    for blob in blobs_list:
        slug_new = blob.name.split("/")[2]
        if slug_new in result.keys():
            result[slug_new] += 1
        else:
            result[slug_new] = 1
    return result

def check_files(date: str):
    companies = greenhouse.fetch_companies()
    slugs = []
    for company in companies:
        slug = company.external_id
        slugs.append(slug)
    company_slugs = set(slugs)
    counts = files_per_company(date)
    #files = set(counts)
    evaluate_files(company_slugs, counts, date)
    file_count = sum(counts.values())
    return file_count

def evaluate_files(expected: set, counts: dict, date: str):
    missing = expected - set(counts)
    total = len(expected)
    non_missing = total - len (missing)
    file_count = sum(counts.values())
    logger.info(f"Files for {date}: {file_count}, {non_missing}/{total} companies")
    if file_count == 0:
        raise ValueError(f"No files written for date: {date}.")
    elif (len(missing) > total/2):
        raise ValueError(f"{len(missing)} out of {total} companies missing: {", ".join(sorted(missing))}. Date: {date}.")
    elif len(missing) > 0:
        logger.warning(f"{len(missing)} out of {total} companies missing for {date}: {", ".join(sorted(missing))}")

def staging_stats():
    client = bigquery.Client()
    query = f"SELECT COUNT(*) AS rows_total, COUNT(DISTINCT landed_at) AS files_total FROM `{dataset}.greenhouse_postings_incoming`"
    rows = list(client.query(query).result())
    row = rows[0]
    return row.rows_total, row.files_total

def evaluate_staging(rows_total: int, files_in_staging: int, files_in_gcs: int, date: str):
    if rows_total == 0:
        raise ValueError(f"Staging file is empty for date: {date}.")
    elif files_in_staging != files_in_gcs:
        raise ValueError(f"Number of files different! Files in staging: {files_in_staging}. Files in GCS: {files_in_gcs}. Date: {date}.")
    else:
        logger.info(f"Staging for {date}: {rows_total} rows from {files_in_staging} files (GCS: {files_in_gcs})")

def final_stats():
    client = bigquery.Client()
    query = f"SELECT COUNT(*) AS rows_total, COUNT(DISTINCT id) AS ids_total FROM `{dataset}.greenhouse_postings`"
    rows = list(client.query(query).result())
    row = rows[0]
    return row.rows_total, row.ids_total

def not_merged_count():
    client = bigquery.Client()
    query = f"SELECT COUNT(*) AS not_merged FROM (SELECT DISTINCT id FROM `{dataset}.greenhouse_postings_incoming` EXCEPT DISTINCT SELECT id FROM `{dataset}.greenhouse_postings`)"
    rows = list(client.query(query).result())
    row = rows[0]
    return row.not_merged

def evaluate_final(rows_total: int, ids_total: int, not_merged: int, date: str):
    if rows_total != ids_total:
        raise ValueError(f"There are duplicate keys in the table for date: {date}. Rows total: {rows_total}. IDs total: {ids_total}.")
    elif not_merged > 0:
        raise ValueError(f"{not_merged} IDs never made it to the table for date: {date}.")
    else:
        logger.info(f"Final table after {date}: {rows_total} rows, {ids_total} distinct ids, {not_merged} not merged")

def run_checks(date: str):
    require_date(date)
    file_count = check_files(date)
    rows_total, files_in_staging = staging_stats()
    evaluate_staging(rows_total, files_in_staging, file_count, date)
    rows_final, ids_final = final_stats()
    not_merged = not_merged_count()
    evaluate_final(rows_final, ids_final, not_merged, date)
    null_counts, staging_rows = fetch_null_counts()
    report_fill_rates(null_counts, staging_rows, date)

def fetch_null_counts():
    client = bigquery.Client()
    query = f"""SELECT 
        COUNTIF (title is NULL) AS title, 
        COUNTIF (url is NULL) AS url,
        COUNTIF (location is NULL) AS location,
        COUNTIF (company is NULL) AS company,
        COUNTIF (department is NULL) AS department,
        COUNTIF (office is NULL) AS office,
        COUNTIF (language is NULL) AS language,
        COUNTIF (updated_at is NULL) AS updated_at,
        COUNTIF (published_at is NULL) AS published_at,
        COUNTIF (deadline_at is NULL) AS deadline_at,
        COUNT(*) AS n_rows
    FROM `{dataset}.greenhouse_postings_incoming`
    """
    rows = list(client.query(query).result())
    row = dict(rows[0])
    n_rows = row.pop("n_rows")
    return row, n_rows

def report_fill_rates(null_counts: dict, n_rows: int, date: str) -> None:
    if n_rows == 0:
        logger.info(f"No rows in staging for {date}, no fill rates.")
    else:
        for name, nulls in null_counts.items():
            filled = n_rows - nulls
            pct = round(filled/n_rows * 100, 1)
            logger.info(f"fill rate {date}: {name:<14} {pct}% ({filled}/{n_rows})")

if __name__ == "__main__":
    import sys
    import datetime
    # Only when run as a script: Airflow configures logging itself.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    run_checks(date)
