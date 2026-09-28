import logging
import json
from ingestion import loader

logger = logging.getLogger(__name__)

# English first (the product's main audience), then Portuguese, then whatever the posting has.
PREFERRED_LANGUAGES = ["en", "pt"]

def choose_language(translations: dict | None) -> str | None:
    """The translation to store for a posting, or None if it has none."""
    if not translations:
        return None
    for language in PREFERRED_LANGUAGES:
        if language in translations:
            return language
    return sorted(translations)[0]

def transform(job: dict) -> dict:
    translations = job.get("translations") or {}
    language = choose_language(translations)
    # No translations at all: fall back to the top-level fields, which hold one version.
    text = translations[language] if language else job
    salary = job.get("salary") or {}
    transformed_job = {}
    transformed_job["id"] = job["id"]
    transformed_job["title"] = text.get("title")
    transformed_job["language"] = language
    transformed_job["url"] = job.get("careers_url")
    transformed_job["location"] = job.get("location")
    transformed_job["remote"] = job.get("remote")
    transformed_job["hybrid"] = job.get("hybrid")
    transformed_job["on_site"] = job.get("on_site")
    transformed_job["country_code"] = job.get("country_code")
    transformed_job["department"] = job.get("department")
    transformed_job["employment_type"] = job.get("employment_type_code")
    transformed_job["content"] = text.get("description")
    transformed_job["requirements"] = text.get("requirements")
    transformed_job["highlight"] = text.get("highlight")
    transformed_job["salary_min"] = salary.get("min")
    transformed_job["salary_max"] = salary.get("max")
    transformed_job["salary_currency"] = salary.get("currency")
    transformed_job["salary_period"] = salary.get("period")
    transformed_job["published_at"] = job.get("published_at")
    transformed_job["updated_at"] = job.get("updated_at")
    transformed_job["raw"] = json.dumps(job)

    return transformed_job

def parse_rows(content: bytes) -> list[dict]:
    """Recruitee: one JSON object wrapping the postings under 'offers'."""
    data = json.loads(content)
    return [transform(job) for job in data["offers"]]

def date_run(date: str) -> dict:
    return loader.run_load("recruitee", parse_rows, date)


if __name__ == "__main__":
    import sys
    import datetime
    # Only when run as a script: Airflow configures logging itself.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    date_run(date)
