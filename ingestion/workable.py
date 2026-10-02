import json
import logging
from collections.abc import Callable
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from google.cloud import bigquery
from ingestion import ats

logger = logging.getLogger(__name__)

LIST_URL = "https://apply.workable.com/api/v1/widget/accounts/{slug}"
DETAIL_URL = "https://apply.workable.com/api/v1/accounts/{slug}/jobs/{shortcode}"

# Workable's job list has no description: the text needs one more request per job. Fetching
# it for every job every night would be ~29k requests (~3h), so details are fetched only for
# jobs whose detail we do not have - and at most this many per run. The first nights work
# through the backlog; after that a night needs only the new jobs.
MAX_DETAILS_PER_RUN = 3000
# A detail older than this is fetched again, so edited descriptions are eventually picked up.
DETAIL_MAX_AGE_DAYS = 30

# Workable rate-limits the detail endpoint with a 429 whose Retry-After can be ~24 hours. The
# shared ats.session obeys Retry-After, so one such answer froze a run for a day. This session
# retries server errors only and never sleeps on a 429: the extract handles it (see below).
session = requests.Session()
session.mount("https://", HTTPAdapter(max_retries=Retry(
    total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504],
    allowed_methods=["GET"], respect_retry_after_header=False)))

def fetch_known_ids(date: str) -> set[str]:
    """Jobs whose detail we already hold and is still fresh, as of the run's logical date."""
    client = bigquery.Client()
    query = f"""
        SELECT id FROM `{ats.dataset}.workable_postings`
        WHERE detail_fetched_at >= TIMESTAMP_SUB(TIMESTAMP(@date), INTERVAL @days DAY)
    """
    config = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("date", "STRING", date),
        bigquery.ScalarQueryParameter("days", "INT64", DETAIL_MAX_AGE_DAYS),
    ])
    return {row.id for row in client.query(query, job_config=config).result()}

def shortcodes_to_detail(jobs: list[dict], known: set[str], budget: int) -> list[str]:
    """Which of a board's jobs get a detail request now: unknown ones, up to the budget left."""
    # dict.fromkeys de-duplicates in order: the list repeats a job once per location, and
    # without it a job with 12 locations would cost 12 identical detail requests.
    wanted = list(dict.fromkeys(job["shortcode"] for job in jobs
                                if job.get("shortcode") and job["shortcode"] not in known))
    return wanted[:max(budget, 0)]

def make_fetch(known: set[str], max_details: int) -> Callable[[str], bytes | None]:
    """A fetch function for ats.run_extract that shares one detail budget across all boards."""
    budget = {"left": max_details, "fetched": 0, "deferred": 0, "rate_limited": False}

    def fetch_workable_raw(slug: str) -> bytes | None:
        try:
            response = session.get(LIST_URL.format(slug=slug), timeout=15)
            response.raise_for_status()
            account = response.json()
        except (requests.exceptions.RequestException, ValueError) as e:
            logger.error(f"Fetch failed for {slug}: {e}")
            return None
        jobs = account.get("jobs") or []
        chosen = shortcodes_to_detail(jobs, known, budget["left"])
        unknown = {j.get("shortcode") for j in jobs if j.get("shortcode") and j["shortcode"] not in known}
        budget["deferred"] += len(unknown) - len(chosen)
        details: dict[str, dict] = {}
        requested = 0
        for shortcode in chosen:
            requested += 1
            try:
                d = session.get(DETAIL_URL.format(slug=slug, shortcode=shortcode), timeout=15)
                if d.status_code == 429:
                    # Circuit breaker: stop asking for details for the rest of this run. Lists
                    # carry on, the jobs load without text, and tomorrow's run picks them up.
                    budget["rate_limited"] = True
                    budget["left"] = 0
                    logger.warning(f"Workable rate limit hit after {budget['fetched'] + len(details)} "
                                   f"details this run (Retry-After: {d.headers.get('retry-after')}s); "
                                   f"no more detail requests until the next run")
                    break
                d.raise_for_status()
                details[shortcode] = d.json()
            except (requests.exceptions.RequestException, ValueError) as e:
                # One missing detail must not cost the board: the job loads without its text
                # and, still unknown, is tried again next run.
                logger.warning(f"Detail failed for {slug}/{shortcode}: {e}")
        budget["deferred"] += len(chosen) - requested if budget["rate_limited"] else 0
        budget["left"] = max(budget["left"] - requested, 0)
        budget["fetched"] += len(details)
        # One file per board, as for every source: the list response and today's detail
        # responses, each kept whole, inside an envelope of our own.
        return json.dumps({"account": account, "details": details}).encode()

    fetch_workable_raw.budget = budget  # type: ignore[attr-defined]
    return fetch_workable_raw

def date_run(date: str) -> dict:
    known = fetch_known_ids(date)
    fetch = make_fetch(known, MAX_DETAILS_PER_RUN)
    summary = ats.run_extract("workable", fetch, date)
    b = fetch.budget  # type: ignore[attr-defined]
    logger.info(f"Workable details for {date}: {b['fetched']} fetched, {b['deferred']} deferred "
                f"to later runs (cap {MAX_DETAILS_PER_RUN}), {len(known)} already known"
                + (" - stopped early by the rate limit" if b["rate_limited"] else ""))
    summary["details_fetched"] = b["fetched"]
    summary["details_deferred"] = b["deferred"]
    summary["details_rate_limited"] = b["rate_limited"]
    return summary

if __name__ == "__main__":
    import sys
    import datetime
    # Only when run as a script: Airflow configures logging itself.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    date_run(date)
