# Runbook — Greenhouse ingestion

What to do when the daily DAG (`greenhouse_ingestion`, 01:30 UTC) fails. Every alert names
the DAG, task, `ds` (the date the run is *for*), run id, attempt and the error.

**First three things, always:**

1. Read the failing task's log in the UI, or `./bin/airflow tasks logs <dag_id> <task_id> <run_id>`.
2. Note the **`ds`**. Everything below operates on that date, not on "today".
3. Reruns are safe. The load is idempotent, and same-day reruns are deduplicated by
   `landed_at`. When in doubt, rerun rather than patch data by hand.

**Rerunning:** clear the task in the UI (Task → Clear), or run the step directly:

```bash
python -m ingestion.greenhouse <ds>          # extract + land
python -m ingestion.greenhouse_loader <ds>   # load staging + merge
python -m ingestion.greenhouse_checks <ds>   # checks only
```

---

## `All N companies failed for <ds>`

**Means:** every Greenhouse request failed. It's our side or theirs, not one company.

**Check:** is the API reachable at all —
`curl -s -o /dev/null -w '%{http_code}\n' 'https://boards-api.greenhouse.io/v1/boards/gitlab/jobs'`
(200 = fine). If that works from your laptop, check the VPS has network and the run isn't
hitting a rate limit (many companies, all failing at once).

**Fix:** once the API answers, rerun `extract` for that `ds`, then `load` and `check`. If
Greenhouse is down, wait — the next day's run re-fetches everything anyway, since the API
only ever returns currently-open jobs.

## `No companies found in the registry for ats='greenhouse'`

**Means:** the driving table `dev_raw.companies` returned no rows. Nothing was attempted.

**Check:** `bq query --use_legacy_sql=false 'SELECT ats, COUNT(*) FROM dev_raw.companies GROUP BY ats'`
— is the table empty, or is the `ats` value wrong (`Greenhouse` instead of `greenhouse`)?

**Fix:** restore or re-seed the rows, then rerun `extract`. Remember `ats` is compared in
code and is case-sensitive.

## `No files written for date: <ds>` (check C1)

**Means:** nothing landed in GCS for that date. Either `extract` never ran, or it ran for a
different date.

**Check:** was `extract` green for this run? Does the folder exist —
`gcloud storage ls "gs://$NAME_BUCKET/greenhouse/ingest_date=<ds>/"`. Also look for a
folder named `ingest_date=None`, which means a run was triggered without a logical date.

**Fix:** rerun `extract` for that `ds`, then `load`. Trigger from the CLI *with* a date:
`./bin/airflow dags trigger greenhouse_ingestion --logical-date "$(date -u +%FT%TZ)"`.

## `N out of M companies missing for <ds>: ...` (check C1, blocking)

**Means:** more than half the companies produced no file. Individual companies fail
occasionally; more than half points at something shared — network, credentials, rate limits.

**Check:** the `extract` log lists each failure with its reason (`Fetch failed for <slug>: ...`).
Look at whether the errors are all the same kind. Try one slug by hand:
`python -c 'import sys; sys.path.insert(0, "."); from ingestion import greenhouse; print(len(greenhouse.fetch_greenhouse_raw("gitlab") or b""))'`

**Fix:** if it was transient, rerun `extract` + `load` + `check`. If those companies really
are gone from Greenhouse (404 each), remove or correct their rows in `dev_raw.companies`.

## `WARNING: N out of M companies missing` (check C1, non-blocking)

**Means:** a few companies failed; the run continued on purpose.

**Check:** the named slugs in the `extract` log. A company that fails for several days in a
row has usually renamed or closed its board.

**Fix:** nothing urgent. Correct the registry when a slug is permanently dead.

## `Staging table is empty for date: <ds>` (check C2)

**Means:** the load ran but inserted nothing.

**Check:** are there files for that date in GCS? Did `load` log
`Loaded 0 rows into staging`? Files that exist but contain no jobs would also do this.

**Fix:** if files exist, rerun `load` for that `ds`. If they don't, this is really the
"no files" case above: rerun `extract` first.

## `Number of files different! Files in staging: X. Files in GCS: Y` (check C2)

**Means:** staging was not built from this day's files. Almost always Y > X: an `extract`
landed files that no `load` has processed yet (for example a manual extract, or a load that
died).

**Check:** compare
`gcloud storage ls "gs://$NAME_BUCKET/greenhouse/ingest_date=<ds>/**" | wc -l`
with `SELECT COUNT(DISTINCT landed_at) FROM dev_raw.greenhouse_postings_incoming`.

**Fix:** rerun `load` for that `ds`, then `check`. X > Y instead means staging holds files
that are no longer in GCS — someone deleted objects; investigate before rerunning.

## `There are duplicate keys in the table` (check C3)

**Means:** the final table has more rows than distinct `id`s. The MERGE should make this
impossible, so treat it as a real bug rather than a blip.

**Check:**
```sql
SELECT id, COUNT(*) c FROM dev_raw.greenhouse_postings GROUP BY id HAVING c > 1 LIMIT 10
```
Then look at whether the MERGE ran, or whether something inserted rows directly.

**Fix:** don't paper over it. Find the source first. BigQuery keeps 7 days of history, so
the previous state can be inspected with
`SELECT ... FROM dev_raw.greenhouse_postings FOR SYSTEM_TIME AS OF TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)`.

## `N IDs never made it to the table` (check C4)

**Means:** ids present in staging are missing from the final table: the MERGE didn't run, or
ran against the wrong dataset.

**Check:** did `load` log `Merged staging into the final table`? Is `NAME_DATASET` the same
for the load and the checks (`/opt/airflow/.env` on the VPS)?

**Fix:** rerun `load` for that `ds` (it reloads staging and re-merges), then `check`.

## `date is required as a YYYY-MM-DD string, got: None`

**Means:** the run has no logical date. Usually a CLI trigger without `--logical-date`.

**Check:** the run id in the alert — a manual run with an empty logical date.

**Fix:** trigger again with a date, as shown above. Also check GCS for an
`ingest_date=None/` folder from an earlier attempt and delete it if present.

## A task timed out, or retried twice and gave up

**Means:** the task ran longer than 20 minutes (`execution_timeout`), or failed 3 times.

**Check:** the log's timings. A slow network makes the extract crawl; the VPS normally
finishes it in about 25 seconds. Check the VPS has memory and disk free:
`ssh <vps> 'free -h; df -h /'`.

**Fix:** rerun the failed task. If it's slow but healthy, raise `execution_timeout` in the
DAG rather than leaving runs to be killed halfway.

## The DAG didn't run at all

No alert fires for this: nothing failed, because nothing ran. This is what the staleness
check exists for.

**Check:** is the DAG paused in the UI? Is Airflow up —
`./bin/airflow dags list`? Are the containers healthy —
`ssh <vps> 'cd /opt/airflow && docker compose ps'`? Any import error —
`./bin/airflow dags list-import-errors`?

**Fix:** unpause, restart the containers (`docker compose up -d`), or fix the import error.
Then trigger a run for the missed date, with `--logical-date`.
