import requests
import datetime
import os
#import argparse
from google.cloud import storage, bigquery

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
        print(f"An error has occured: {e}. Something is wrong with {slug}")
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
        print(row.name)
    return results_list

def date_run(date: str):
    companies = fetch_companies()
    for company in companies:
        slug = company.external_id
        raw = fetch_greenhouse_raw(slug)
        if raw != None:
            print(f"Fetched {len(raw)} bytes")
            path = land_raw_json(date, raw, source="greenhouse", slug=slug)
            print(f"Landed to gs://{bucket_name}/{path}")
        else:
            print("Error occured")


if __name__ == "__main__":
    date_run(datetime.date.today().isoformat())
    

    