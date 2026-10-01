# Runbook — ATS ingestion

What to do when a daily ingestion DAG fails. There is one per source, all with the same
tasks (`extract >> load >> check`) and the same shared code, so every entry below applies to
all of them — substitute the source:

| DAG | Source (`<source>`) | Schedule (UTC) |
|---|---|---|
| `greenhouse_ingestion` | `greenhouse` | 01:30 |
| `lever_ingestion` | `lever` | 02:30 |
| `ashby_ingestion` | `ashby` | 03:30 |
| `recruitee_ingestion` | `recruitee` | 04:30 (timeout 120 min) |
| `teamtailor_ingestion` | `teamtailor` | 05:30 (timeout 90 min) |

Every alert names the DAG, task, `ds` (the date the run is *for*), run id, attempt and the
error.

**First three things, always:**

1. Read the failing task's log in the UI, or `./bin/airflow tasks logs <dag_id> <task_id> <run_id>`.
2. Note the **`ds`**. Everything below operates on that date, not on "today".
3. Reruns are safe. The load is idempotent, and same-day reruns are deduplicated by
   `landed_at`. When in doubt, rerun rather than patch data by hand.

**Rerunning:** clear the task in the UI (Task → Clear), or run the step directly:

```bash
python -m ingestion.<source> <ds>            # extract + land
python -m ingestion.<source>_loader <ds>     # load staging + merge
python -m ingestion.checks <source> <ds>     # checks only
```

---

## `All N companies failed for <ds>`

**Means:** every request to that source failed. It's our side or theirs, not one company.

**Check:** is the API reachable at all (200 = fine) —
`curl -sS -o /dev/null -w '%{http_code}\n' 'https://boards-api.greenhouse.io/v1/boards/gitlab/jobs'`,
`curl -sS -o /dev/null -w '%{http_code}\n' 'https://api.lever.co/v0/postings/<any-slug>?mode=json'`,
`curl -sS -o /dev/null -w '%{http_code}\n' 'https://api.ashbyhq.com/posting-api/job-board/<any-slug>'`. If that works from your laptop, check the VPS has network and the run isn't
hitting a rate limit (many companies, all failing at once).

**Fix:** once the API answers, rerun `extract` for that `ds`, then `load` and `check`. If
the source is down, wait — the next day's run re-fetches everything anyway, since the API
only ever returns currently-open jobs.

## `No companies found in the registry for ats='<source>'`

**Means:** the driving table `dev_raw.companies` returned no rows. Nothing was attempted.

**Check:** `bq query --use_legacy_sql=false 'SELECT ats, COUNT(*) FROM dev_raw.companies GROUP BY ats'`
— is the table empty, or is the `ats` value wrong (`Greenhouse` instead of `greenhouse`)?

**Fix:** restore or re-seed the rows, then rerun `extract`. Remember `ats` is compared in
code and is case-sensitive.

## `No files written for date: <ds>` (check C1)

**Means:** nothing landed in GCS for that date. Either `extract` never ran, or it ran for a
different date.

**Check:** was `extract` green for this run? Does the folder exist —
`gcloud storage ls "gs://$NAME_BUCKET/<source>/ingest_date=<ds>/"`. Also look for a
folder named `ingest_date=None`, which means a run was triggered without a logical date.

**Fix:** rerun `extract` for that `ds`, then `load`. Trigger from the CLI *with* a date:
`./bin/airflow dags trigger <source>_ingestion --logical-date "$(date -u +%FT%TZ)"`.

## `N companies landed no file for <ds> although the extract reported success` (check C1, blocking)

**Means:** the extract said these boards landed, and their files are not in GCS. There is no
threshold: an *unexplained* absence is always a bug (a landing path mismatch, a date
mismatch between tasks, deleted objects), whatever the count.

**Check:** the `extract` log for those slugs (`[i/N] ...` lines) and the GCS folder for that
`ds`. Look for a folder under a different date or a differently spelled slug — on
2026-09-28 percent-encoded slugs (`it%20labs`) produced `%20` folders.

**Fix:** find the mismatch before rerunning; a rerun that repeats it will fail the same way.

## `N of M companies failed to fetch for <ds> (no file expected)` (check C1, warning)

**Means:** a few boards could not be fetched, the extract reported them in `failed_slugs`,
and the run continued on purpose — an *explained* absence.

**Check:** the named slugs in the `extract` log (`No data landed for <slug>`, with the HTTP
error just above). A board that fails several days in a row has usually renamed or closed.
Try one by hand:
`python -c 'import sys; sys.path.insert(0, "."); from ingestion import greenhouse; print(len(greenhouse.fetch_greenhouse_raw("gitlab") or b""))'`
(swap in `lever.fetch_lever_raw` / `ashby.fetch_ashby_raw`).

**Fix:** nothing urgent. Remove or correct the row in `dev_raw.companies` when a slug is
permanently dead (404 each day).

## `N out of M companies missing` (check C1, only when run from the CLI)

**Means:** run without the extract's summary (`python -m ingestion.checks`), C1 cannot tell
explained from unexplained absences, so it falls back to a threshold: more than half missing
raises, fewer warns.

**Fix:** as above; in the DAG this case does not occur.

## `Returned exactly the number of jobs as Per Page: N, for company <slug>` (Teamtailor extract)

**Means:** a Teamtailor feed returned exactly `PER_PAGE` items. The feed silently caps results
(100 by default, which is why the extract asks for 10,000); a count equal to the request is a
ceiling, not a total. The board is treated as failed rather than landed truncated.

**Check:** `curl -sS "https://<slug>.teamtailor.com/jobs.rss?per_page=20000" | grep -o "<item>" | wc -l`
- if that is larger, Teamtailor added (or lowered) a limit.

**Fix:** raise `PER_PAGE` in `ingestion/teamtailor.py` if the feed honours a bigger value; if
it is now capped hard, the extract needs offset paging (`?offset=`), which the feed supported
when examined.

## `Staging is empty for date: <ds>` (check C2)

**Means:** the load ran but inserted nothing.

**Check:** are there files for that date in GCS? Did `load` log
`Loaded 0 rows into staging`? Files that exist but contain no jobs would also do this.

**Fix:** if files exist, rerun `load` for that `ds`. If they don't, this is really the
"no files" case above: rerun `extract` first.

## `Number of files different! Files in staging: X. Files expected: Y` (check C2)

**Means:** staging was not built from exactly the files the load reported. In the DAG, `Y` is
the loader's own `files_with_rows` (boards with zero open jobs legitimately produce no rows,
so they are not counted). A mismatch means an `extract` landed files after the `load` read
the folder (a manual extract, or a retry overlapping), or a load died halfway.

**Check:** compare
`gcloud storage ls "gs://$NAME_BUCKET/<source>/ingest_date=<ds>/**" | wc -l`
with `SELECT COUNT(DISTINCT landed_at) FROM dev_raw.<source>_postings_incoming`.

**Fix:** rerun `load` for that `ds`, then `check`.

## `Staging holds more files than exist for <ds>` (check C2)

**Means:** staging has rows from files that are not in this day's folder — rows from another
day, or objects deleted after loading. Investigate before rerunning.

## `There are duplicate keys in the table` (check C3)

**Means:** the final table has more rows than distinct `id`s. The MERGE should make this
impossible, so treat it as a real bug rather than a blip.

**Check:**
```sql
SELECT id, COUNT(*) c FROM dev_raw.<source>_postings GROUP BY id HAVING c > 1 LIMIT 10
```
Then look at whether the MERGE ran, or whether something inserted rows directly.

**Fix:** don't paper over it. Find the source first. BigQuery keeps 7 days of history, so
the previous state can be inspected with
`SELECT ... FROM dev_raw.<source>_postings FOR SYSTEM_TIME AS OF TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)`.

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

**Means:** the task ran longer than 45 minutes (`execution_timeout`, per task), or failed
3 times.

**Check:** the log's timings against the baselines: at ~200-400 boards each, extract and load
take ~12-17 minutes. Duration grows with the number of registered boards, so a registry that
just grew is the first suspect. Check the VPS has memory and disk free:
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
