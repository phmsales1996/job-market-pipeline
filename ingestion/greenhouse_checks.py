import os
from google.cloud import storage, bigquery
from ingestion import greenhouse

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

def evaluate_files(expected: set, counts: dict, date: str):
    missing = expected - set(counts)
    total = len(expected)
    non_missing = total - len (missing)
    file_count = sum(counts.values())
    print(f"Files for {date}: {file_count}, {non_missing}/{total} companies.")
    if file_count == 0:
        raise ValueError(f"No files written for date: {date}.")
    elif (len(missing) > total/2):
        raise ValueError(f"{len(missing)} out of {total} companies missing: {", ".join(sorted(missing))}. Date: {date}.")
    elif len(missing) > 0:
        print(f"Warning: {len(missing)} out of {total} companies missing: {",".join(sorted(missing))}. Date: {date}.")