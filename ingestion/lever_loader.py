import logging
import json
from ingestion import loader
import datetime

logger = logging.getLogger(__name__)

def epoch_ms_to_iso(ms: int | None) -> str | None:
    """Lever timestamps are epoch MILLISECONDS; Greenhouse sends ISO strings.

    Returns None when the source sent nothing, rather than raising: a posting with no
    createdAt must not take the whole load down with it.
    """
    if ms is None:
        return None
    return datetime.datetime.fromtimestamp(ms / 1000, tz=datetime.timezone.utc).isoformat()

def transform(job: dict) -> dict:
    transformed_job = {}
    transformed_job["id"] = job["id"]
    transformed_job["title"] = job.get("text")
    transformed_job["url"] = job.get("hostedUrl")
    transformed_job["raw"] = json.dumps(job)
    transformed_job["location"] = (job.get("categories") or {}).get("location")
    transformed_job["department"] = (job.get("categories") or {}).get("team")
    transformed_job["commitment"] = (job.get("categories") or {}).get("commitment")
    transformed_job["workplace_type"] = job.get("workplaceType")
    transformed_job["country"] = job.get("country")
    transformed_job["content"] = job.get("description")
    transformed_job["additional"] = job.get("additional")
    transformed_job["salary_min"] = (job.get("salaryRange") or {}).get("min")
    transformed_job["salary_max"] = (job.get("salaryRange") or {}).get("max")
    transformed_job["salary_currency"] = (job.get("salaryRange") or {}).get("currency")
    transformed_job["salary_interval"] = (job.get("salaryRange") or {}).get("interval")
    transformed_job["published_at"] = epoch_ms_to_iso(job.get("createdAt"))

    return transformed_job

def parse_rows(content: bytes) -> list[dict]:
    """Lever: the payload is a bare JSON array of postings, with no wrapper object."""
    data = json.loads(content)
    return [transform(job) for job in data]

def date_run(date: str) -> dict:
    return loader.run_load("lever", parse_rows, date)


if __name__ == "__main__":
    import sys
    import datetime
    # Only when run as a script: Airflow configures logging itself.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    date_run(date)
