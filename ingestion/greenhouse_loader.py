import logging
import json
from typing import Any
from ingestion import loader

logger = logging.getLogger(__name__)

def first_field(items: list | None, key: str) -> Any:
    if items:
        return items[0][key]
    else:
        return None

def transform(job: dict) -> dict:
    transformed_job = {}
    transformed_job["id"] = job["id"]
    transformed_job["title"] = job.get("title")
    transformed_job["url"] = job.get("absolute_url")
    transformed_job["company"] = job.get("company_name")
    transformed_job["language"] = job.get("language")
    transformed_job["content"] = job.get("content")
    transformed_job["updated_at"] = job.get("updated_at")
    transformed_job["published_at"] = job.get("first_published")
    transformed_job["deadline_at"] = job.get("application_deadline")
    transformed_job["raw"] = json.dumps(job)
    transformed_job["location"] = (job.get("location") or {}).get("name")
    transformed_job["department"] = first_field(job.get("departments"), "name")
    transformed_job["office"] = first_field(job.get("offices"), "location")

    return transformed_job

def parse_rows(content: bytes) -> list[dict]:
    """Greenhouse: one JSON object wrapping the postings under 'jobs'."""
    data = json.loads(content)
    return [transform(job) for job in data["jobs"]]

def date_run(date: str) -> dict:
    return loader.run_load("greenhouse", parse_rows, date)


if __name__ == "__main__":
    import sys
    import datetime
    # Only when run as a script: Airflow configures logging itself.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    date_run(date)
