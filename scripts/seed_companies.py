"""Validate ATS board slugs and seed them into the companies registry.

A one-off utility, not part of the daily pipeline. Slugs collected elsewhere go
stale — boards get renamed, closed or moved — so each one is checked against the
source's API before it reaches the registry.

    python scripts/seed_companies.py greenhouse slugs.json           # validate only
    python scripts/seed_companies.py lever slugs.json --insert       # validate, then insert
    python scripts/seed_companies.py lever slugs.json --insert --limit 50

The input is either a JSON list of slugs, or a dict keyed by ATS (e.g.
{"greenhouse": [...], "lever": [...]}), in which case the chosen source's list is used.
Inserting is idempotent: slugs already in the registry are skipped.

Each source needs one validator, registered in VALIDATORS below. Greenhouse reports the
company's real name in its payload; Lever does not, so its name is derived from the slug
(see name_from_slug) — lossy, and recorded as such in the companies table description.
"""

import argparse
import json
import logging
import pathlib
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from urllib.parse import unquote

from google.cloud import bigquery

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from ingestion.ats import dataset, session  # noqa: E402  (shared retrying session)

logger = logging.getLogger("seed_companies")

# Lighter than the extractor's call: the descriptions are what make responses big,
# and validation only needs to know the board exists and what it is called.
GREENHOUSE_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
LEVER_URL = "https://api.lever.co/v0/postings/{slug}?mode=json"
ASHBY_URL = "https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"
RECRUITEE_URL = "https://{slug}.recruitee.com/api/offers/"
TEAMTAILOR_URL = "https://{slug}.teamtailor.com/jobs.rss?per_page=10000"


def name_from_slug(slug: str) -> str:
    """'people-ai' -> 'People Ai'. Lossy on purpose: better than nothing, worse than real.

    Used only for sources whose payload carries no company name.
    """
    return slug.replace("-", " ").replace("_", " ").title()


def check_greenhouse(slug: str) -> tuple[bool, str, int]:
    """Return (alive, company_name_or_reason, n_jobs)."""
    try:
        response = session.get(GREENHOUSE_URL.format(slug=slug), timeout=15)
        response.raise_for_status()
        jobs = response.json().get("jobs", [])
    except Exception as e:  # noqa: BLE001 - one dead board must not stop the sweep
        return False, str(e).split(" for url")[0], 0
    name = jobs[0].get("company_name") if jobs else None
    return True, name or name_from_slug(slug), len(jobs)


def check_lever(slug: str) -> tuple[bool, str, int]:
    """Same contract as check_greenhouse; the payload is a bare array with no company name."""
    try:
        response = session.get(LEVER_URL.format(slug=slug), timeout=15)
        response.raise_for_status()
        jobs = response.json()
    except Exception as e:  # noqa: BLE001
        return False, str(e).split(" for url")[0], 0
    return True, name_from_slug(slug), len(jobs)

def check_ashby(slug: str) -> tuple[bool, str, int]:
    try:
        response = session.get(ASHBY_URL.format(slug=slug), timeout=15)
        response.raise_for_status()
        jobs = response.json().get("jobs", [])
    except Exception as e:  # noqa: BLE001
        return False, str(e).split(" for url")[0], 0
    return True, name_from_slug(slug), len(jobs)

def check_recruitee(slug: str) -> tuple[bool, str, int]:
    try:
        response = session.get(RECRUITEE_URL.format(slug=slug), timeout=15)
        response.raise_for_status()
        jobs = response.json().get("offers", [])
    except Exception as e:  # noqa: BLE001
        return False, str(e).split(" for url")[0], 0
    return True, name_from_slug(slug), len(jobs)

def check_teamtailor(slug: str) -> tuple[bool, str, int]:
    """Same contract as the others, but the payload is RSS: no JSON to parse, so 'is this
    really a feed?' is answered by the content type, and the channel title is the real name."""
    try:
        response = session.get(TEAMTAILOR_URL.format(slug=slug), timeout=15)
        response.raise_for_status()
        if "xml" not in response.headers.get("content-type", ""):
            return False, "not an RSS feed (200 but no XML)", 0
        n_jobs = response.content.count(b"<item>")
        name = ET.fromstring(response.content).findtext("channel/title")
    except Exception as e:  # noqa: BLE001
        return False, str(e).split(" for url")[0], 0
    return True, name or name_from_slug(slug), n_jobs


VALIDATORS: dict[str, Callable[[str], tuple[bool, str, int]]] = {
    "greenhouse": check_greenhouse,
    "lever": check_lever,
    "ashby": check_ashby,
    "recruitee": check_recruitee,
    "teamtailor": check_teamtailor
}


def read_slugs(path: str, source: str) -> list:
    data = json.loads(pathlib.Path(path).read_text())
    slugs = data[source] if isinstance(data, dict) else data
    # Slugs scraped from URLs can arrive percent-encoded ('it%20labs'). Decode before
    # de-duplicating, or 'it labs' and 'it%20labs' become two registry rows for one board.
    return sorted(dict.fromkeys(unquote(slug) for slug in slugs))  # de-duplicate, keep it stable


def existing_slugs(client: bigquery.Client, source: str) -> set:
    query = f"SELECT external_id FROM `{dataset}.companies` WHERE ats = @ats"
    config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("ats", "STRING", source)]
    )
    return {row.external_id for row in client.query(query, job_config=config).result()}


def insert_companies(client: bigquery.Client, source: str, rows: list) -> int:
    """Insert (name, external_id) pairs that are not in the registry yet."""
    if not rows:
        return 0
    query = f"""
        INSERT INTO `{dataset}.companies` (name, external_id, ats)
        SELECT name, external_id, @ats
        FROM UNNEST(@companies) AS c
    """
    config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("ats", "STRING", source),
            bigquery.ArrayQueryParameter(
                "companies",
                bigquery.StructQueryParameterType(
                    bigquery.ScalarQueryParameterType("STRING", name="name"),
                    bigquery.ScalarQueryParameterType("STRING", name="external_id"),
                ),
                [
                    bigquery.StructQueryParameter(
                        None,
                        bigquery.ScalarQueryParameter("name", "STRING", name),
                        bigquery.ScalarQueryParameter("external_id", "STRING", slug),
                    )
                    for slug, name in rows
                ],
            ),
        ]
    )
    client.query(query, job_config=config).result()
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", choices=sorted(VALIDATORS), help="which ATS these slugs are")
    parser.add_argument("slugs_file", help="JSON list of slugs, or {ats: [slugs]}")
    parser.add_argument("--insert", action="store_true", help="write the live ones to the registry")
    parser.add_argument("--limit", type=int, help="only consider the first N new slugs")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s | %(message)s")

    check_slug = VALIDATORS[args.source]
    client = bigquery.Client()
    known = existing_slugs(client, args.source)
    slugs = [s for s in read_slugs(args.slugs_file, args.source) if s not in known]
    if args.limit:
        slugs = slugs[: args.limit]
    logger.info(f"{args.source}: {len(known)} already in the registry; "
                f"checking {len(slugs)} new slugs")

    live, dead = [], []
    for i, slug in enumerate(slugs, 1):
        ok, detail, n_jobs = check_slug(slug)
        if ok:
            live.append((slug, detail))
        else:
            dead.append((slug, detail))
        if i % 25 == 0 or i == len(slugs):
            logger.info(f"checked {i}/{len(slugs)} - {len(live)} live, {len(dead)} dead")

    logger.info(f"live: {len(live)} | dead: {len(dead)}")
    if dead:
        logger.info("dead slugs: " + ", ".join(slug for slug, _ in dead[:20])
                    + (" ..." if len(dead) > 20 else ""))

    if args.insert:
        inserted = insert_companies(client, args.source, live)
        logger.info(f"inserted {inserted} companies into {dataset}.companies")
    else:
        logger.info("dry run: nothing written (pass --insert to write)")


if __name__ == "__main__":
    main()
