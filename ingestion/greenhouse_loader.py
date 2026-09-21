import datetime
import json
import pathlib
import os
from google.cloud import storage, bigquery

bucket_name = os.environ['NAME_BUCKET']
#path = "greenhouse/ingest_date=2026-09-19/airbnb/221735.json"
today = datetime.date.today().isoformat()
prefix = "greenhouse/ingest_date="+today+"/"

dataset = os.environ['NAME_DATASET']

table_id = dataset+".greenhouse_postings_incoming"

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
 
def transform(job: dict, landed_at: datetime) -> dict:
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
    transformed_job["first_seen_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    transformed_job["last_seen_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    #transformed_job["department"] = job["departments"][0]["name"]
    #transformed_job["office"] = job["offices"][0]["location"]
    transformed_job["department"] = first_field(job["departments"], "name")
    transformed_job["office"] = first_field(job["offices"], "location")
    transformed_job['landed_at'] = landed_at.isoformat()

    return transformed_job

def load_rows(rows: list) -> None:
    client = bigquery.Client()
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE", autodetect=False)
    job = client.load_table_from_json(rows, table_id, job_config=job_config)
    return job.result()

def fetch_files():
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=prefix)
    blobs_list = list(blobs)
    for blob in blobs_list:
        print(blob.name)
    return blobs_list

def run_merge():
    client = bigquery.Client()
    result = client.query(sql_text.format(dataset=dataset)).result()
    return result




if __name__ == "__main__":
    files = fetch_files()
    jobs_loaded = []
    for file in files:
        j = fetch_raw_json(file.name)
        data = json.loads(j)
        #print(type(data))
        #print(data.keys())
        a = len(data["jobs"])
        #print(len(data["jobs"]))
        
        jobs_list = []
        for job in data["jobs"]:
            job_transformed = transform(job, file.time_created)
            jobs_list.append(job_transformed)
        jobs_loaded.extend(jobs_list)
    load_rows(jobs_loaded)
    print("Data loaded into staging successfully!")
    run_merge()
    print("Data loaded into final table successfully!")