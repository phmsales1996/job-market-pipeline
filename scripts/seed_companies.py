"""Validate Greenhouse board slugs and seed them into the companies registry.

A one-off utility, not part of the daily pipeline. Slugs collected elsewhere go
stale — boards get renamed, closed or moved — so each one is checked against the
API before it reaches the registry, and the board's own company name is read from
the response rather than guessed from the slug.

    python scripts/seed_companies.py slugs.json               # validate only
    python scripts/seed_companies.py slugs.json --insert      # validate, then insert
    python scripts/seed_companies.py slugs.json --insert --limit 50

The input is either a JSON list of slugs, or a dict keyed by ATS (e.g.
{"greenhouse": [...], "lever": [...]}), in which case the greenhouse list is used.
Inserting is idempotent: slugs already in the registry are skipped.
"""

import argparse
import json
import logging
import pathlib
import sys

from google.cloud import bigquery

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from ingestion.greenhouse import dataset, session  # noqa: E402  (shared retrying session)

logger = logging.getLogger("seed_companies")

ATS = "greenhouse"
# Lighter than the extractor's call: the descriptions are what make responses big,
# and validation only needs to know the board exists and what it is called.
BOARD_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"


def read_slugs(path: str) -> list:
    data = json.loads(pathlib.Path(path).read_text())
    slugs = data[ATS] if isinstance(data, dict) else data
    return sorted(dict.fromkeys(slugs))  # de-duplicate, keep it stable


def check_slug(slug: str):
    """Return (ok, company_name_or_reason, n_jobs)."""
    try:
        response = session.get(BOARD_URL.format(slug=slug), timeout=15)
        response.raise_for_status()
        jobs = response.json().get("jobs", [])
    except Exception as e:  # noqa: BLE001 - one dead board must not stop the sweep
        return False, str(e).split(" for url")[0], 0
    name = jobs[0].get("company_name") if jobs else None
    return True, name or slug, len(jobs)


def existing_slugs(client: bigquery.Client) -> set:
    query = f"SELECT external_id FROM `{dataset}.companies` WHERE ats = @ats"
    config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("ats", "STRING", ATS)]
    )
    return {row.external_id for row in client.query(query, job_config=config).result()}


def insert_companies(client: bigquery.Client, rows: list) -> int:
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
            bigquery.ScalarQueryParameter("ats", "STRING", ATS),
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
    parser.add_argument("slugs_file", help="JSON list of slugs, or {ats: [slugs]}")
    parser.add_argument("--insert", action="store_true", help="write the live ones to the registry")
    parser.add_argument("--limit", type=int, help="only consider the first N new slugs")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s | %(message)s")

    client = bigquery.Client()
    known = existing_slugs(client)
    slugs = [s for s in read_slugs(args.slugs_file) if s not in known]
    if args.limit:
        slugs = slugs[: args.limit]
    logger.info(f"{len(known)} already in the registry; checking {len(slugs)} new slugs")

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
        inserted = insert_companies(client, live)
        logger.info(f"inserted {inserted} companies into {dataset}.companies")
    else:
        logger.info("dry run: nothing written (pass --insert to write)")


if __name__ == "__main__":
    main()
