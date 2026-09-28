import logging
import json
from ingestion import loader

logger = logging.getLogger(__name__)

def salary_component(job: dict) -> dict:
    """The one 'Salary' entry in compensation.summaryComponents, or {} if there is none or several.

    Never [0]: the list can also hold equity (a percentage) and bonus components.
    """
    components = (job.get("compensation") or {}).get("summaryComponents") or []
    salaries = [c for c in components if c.get("compensationType") == "Salary"]
    if len(salaries) == 1:
        return salaries[0]
    return {}

def transform(job: dict) -> dict:
    salary = salary_component(job)
    transformed_job = {}
    transformed_job["id"] = job["id"]
    transformed_job["title"] = job.get("title")
    transformed_job["url"] = job.get("jobUrl")
    transformed_job["location"] = job.get("location")
    transformed_job["department"] = job.get("department")
    transformed_job["team"] = job.get("team")
    transformed_job["employment_type"] = job.get("employmentType")
    transformed_job["workplace_type"] = job.get("workplaceType")
    transformed_job["country"] = ((job.get("address") or {}).get("postalAddress") or {}).get("addressCountry")
    transformed_job["content"] = job.get("descriptionPlain")
    transformed_job["is_listed"] = job.get("isListed")
    transformed_job["salary_min"] = salary.get("minValue")
    transformed_job["salary_max"] = salary.get("maxValue")
    transformed_job["salary_currency"] = salary.get("currencyCode")
    transformed_job["salary_interval"] = salary.get("interval")
    transformed_job["compensation_summary"] = (job.get("compensation") or {}).get("compensationTierSummary")
    transformed_job["published_at"] = job.get("publishedAt")
    transformed_job["raw"] = json.dumps(job)

    return transformed_job

def parse_rows(content: bytes) -> list[dict]:
    """Ashby: one JSON object wrapping the postings under 'jobs', like Greenhouse."""
    data = json.loads(content)
    return [transform(job) for job in data["jobs"]]

def date_run(date: str) -> dict:
    return loader.run_load("ashby", parse_rows, date)


if __name__ == "__main__":
    import sys
    import datetime
    # Only when run as a script: Airflow configures logging itself.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    date_run(date)
