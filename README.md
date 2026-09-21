# job-market-pipeline

A batch data pipeline that collects public job postings from applicant-tracking systems
(ATS), lands the raw responses in Google Cloud Storage, and loads them into BigQuery. It's
a data-engineering learning project, built one step at a time.

**Status:** one source (Greenhouse) works end to end. Airflow orchestration is being built.

## Architecture

```mermaid
flowchart LR
    A[Greenhouse Job Board API] -->|extractor| B[(GCS landing zone<br/>raw JSON, untouched)]
    C[(BigQuery<br/>raw.companies)] -->|which companies| A
    B -->|loader| D[(BigQuery<br/>raw.greenhouse_postings_incoming<br/>staging, replaced each run)]
    D -->|MERGE on id,<br/>latest file wins| E[(BigQuery<br/>raw.greenhouse_postings<br/>one row per job)]
```

1. **Extract** (`ingestion/greenhouse.py`): reads the list of companies to collect from a
   BigQuery registry table and calls Greenhouse's public Job Board API for each one. The
   response bytes are stored unchanged in GCS at
   `greenhouse/ingest_date=YYYY-MM-DD/<company>/<time>.json`.
2. **Load** (`ingestion/greenhouse_loader.py`): lists everything that landed for the day,
   flattens each job into the target schema, and batch-loads all rows into a staging table.
3. **Merge** (`sql/merge_greenhouse_postings.sql`): upserts staging into the final table
   by job `id`.

## Design decisions

- **ELT with an untouched landing zone.** Raw API responses are stored byte for byte,
  before any parsing, so GCS holds the complete history of every response. Anything
  downstream can be rebuilt from it. The landing path is partitioned by date first, then
  company, so the loader can process "everything that landed today" without knowing the
  company list in advance.
- **The BigQuery raw table is the current state, not the history.** Since GCS already keeps
  every day's files, the table holds one row per job, upserted with `MERGE`.
  `first_seen_at` is set once and `last_seen_at` is updated on every run. This keeps the
  table from growing by a near-duplicate copy of every open job each day.
- **Idempotent loads.** BigQuery does not enforce primary keys, so rerunning a naive insert
  creates duplicates. Instead, each run fully replaces a staging table (`WRITE_TRUNCATE`)
  and then runs `MERGE`, which is safe to repeat.
- **Retries and reruns can't create duplicates.** If an extract runs more than once in a
  day, the same job appears in several landed files. Each staging row records `landed_at`
  (the GCS object's creation time). The `MERGE` source keeps only the newest copy of each
  job (`QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY landed_at DESC) = 1`), so the
  merge never sees two candidates for one target row.
- **Batch load jobs, not streaming inserts.** The data is daily and nothing needs low
  latency. Load jobs are also free, which fits a free-tier budget.
- **Explicit schemas.** Tables are created from the DDL in `sql/`, and loads use
  `autodetect=False`. With autodetection on, a column that happened to be all `NULL` in a
  batch was once inferred as `STRING` instead of the declared `TIMESTAMP`.
- **Configuration comes from the environment.** Bucket and dataset names are never in the
  code. They are read from environment variables, and the process fails immediately if one
  is missing (`os.environ[...]`, not `.get`). The GCP project comes from the environment's
  credentials. SQL that must run against different datasets is a template (`{dataset}`)
  that Python fills in, because BigQuery query parameters can't be used for table names.

## Repository layout

```
ingestion/
  greenhouse.py            extract: companies registry -> Greenhouse API -> GCS
  greenhouse_loader.py     load: GCS -> staging table -> MERGE into the final table
sql/
  create_*.sql             table DDL (run once, by hand)
  merge_greenhouse_postings.sql   MERGE template, run by the loader
```

## Running it locally

Requirements: Python 3.13, a GCP project with a GCS bucket and a BigQuery dataset, and
credentials available to the Google client libraries (for example
`gcloud auth application-default login`, or `GOOGLE_APPLICATION_CREDENTIALS` pointing to a
service-account key).

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

export NAME_BUCKET=<your-landing-bucket>
export NAME_DATASET=<your-raw-dataset>

# once: create the tables (the DDL uses the dev_raw dataset)
bq query --use_legacy_sql=false < sql/create_dev_raw_companies.sql
bq query --use_legacy_sql=false < sql/create_dev_raw_greenhouse_postings.sql
bq query --use_legacy_sql=false < sql/create_dev_raw_greenhouse_postings_incoming.sql
# then add rows to the companies table: name, external_id (the Greenhouse board slug), ats = 'greenhouse'

python ingestion/greenhouse.py          # extract and land
python ingestion/greenhouse_loader.py   # load and merge
```

## Roadmap

- [x] Greenhouse, multiple companies, end to end, idempotent
- [ ] Airflow DAG (self-hosted, Docker) running the daily extract → load → merge
- [ ] Per-company task fan-out with Airflow dynamic task mapping
- [ ] More sources: SmartRecruiters, Breezy HR, Deel, search-based discovery
- [ ] dbt staging and dimensional models, with data-quality tests
- [ ] Separate dev and prod environments
- [ ] Serving layer / dashboard

### Known issues

- `first_seen_at` / `last_seen_at` are written from the machine's local time without a
  time zone, and BigQuery reads them as UTC. The fix is to use a time-zone-aware UTC
  timestamp.
- The run date is computed from the system clock at import time. It should become a
  parameter (Airflow's logical date), so that retries and reruns of a past day read the
  right files.

## License

MIT, see [LICENSE](LICENSE).
