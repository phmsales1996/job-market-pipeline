import logging
import json
from ingestion import loader

logger = logging.getLogger(__name__)

def transform(entries: list[dict], detail: dict | None) -> dict:
    """One row from a list entry plus, when fetched this run, its detail response.

    The two payloads overlap only partly: the list alone has the taxonomy (education,
    experience, industry, function) and the dates; the detail alone has the text, salary,
    workplace and language. Detail columns are None when no detail was fetched today - the
    MERGE then keeps the values already in the table instead of overwriting them.
    """
    # The list repeats a job once per location, each entry carrying only its own location.
    # Location columns come from the first entry; raw keeps every entry, so none is lost.
    job = entries[0]
    detail = detail or {}
    location = (job.get("locations") or [{}])[0]
    transformed_job = {}
    transformed_job["id"] = job["shortcode"]
    transformed_job["title"] = job.get("title")
    transformed_job["url"] = job.get("url")
    transformed_job["city"] = job.get("city")
    transformed_job["region"] = job.get("state")
    transformed_job["country"] = job.get("country")
    transformed_job["country_code"] = location.get("countryCode")
    transformed_job["telecommuting"] = job.get("telecommuting")
    transformed_job["department"] = job.get("department") or None
    transformed_job["employment_type"] = job.get("employment_type") or None
    transformed_job["education"] = job.get("education") or None
    transformed_job["experience"] = job.get("experience") or None
    transformed_job["industry"] = job.get("industry") or None
    transformed_job["job_function"] = job.get("function") or None
    transformed_job["published_on"] = job.get("published_on")
    transformed_job["has_detail"] = bool(detail)
    transformed_job["workplace"] = detail.get("workplace")
    transformed_job["language"] = detail.get("language")
    transformed_job["content"] = job.get("description") or None
    transformed_job["requirements"] = detail.get("requirements")
    transformed_job["benefits"] = detail.get("benefits")
    transformed_job["salary_min"] = detail.get("salary_from")
    transformed_job["salary_max"] = detail.get("salary_to")
    transformed_job["salary_currency"] = detail.get("salary_currency_iso_code")
    transformed_job["salary_frequency"] = detail.get("salary_frequency")
    transformed_job["raw"] = json.dumps(entries)
    transformed_job["raw_detail"] = json.dumps(detail) if detail else None

    return transformed_job

def parse_rows(content: bytes) -> list[dict]:
    """Workable: our envelope {"account": <list response>, "details": {shortcode: <detail>}}."""
    envelope = json.loads(content)
    details = envelope.get("details") or {}
    jobs = (envelope.get("account") or {}).get("jobs") or []
    # One row per job, not per list entry: group the repeated entries, keeping feed order.
    entries_by_job: dict[str, list[dict]] = {}
    for job in jobs:
        entries_by_job.setdefault(job["shortcode"], []).append(job)
    return [transform(entries, details.get(shortcode)) for shortcode, entries in entries_by_job.items()]

def date_run(date: str) -> dict:
    return loader.run_load("workable", parse_rows, date)


if __name__ == "__main__":
    import sys
    import datetime
    # Only when run as a script: Airflow configures logging itself.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    date_run(date)
