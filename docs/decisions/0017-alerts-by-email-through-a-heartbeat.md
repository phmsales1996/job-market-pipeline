# 0017. Alerts by email, through a heartbeat service

Status: accepted, October 2026

## Context
Failures were only written to the task log, on the assumption that a daily look at Airflow would
catch them. It did not: in October two new country values failed a dbt test, and the transform
failed seven nights in a row - with the marts and the dashboard a week stale - before anyone looked.
[0015](0015-transform-when-ingestion-is-over.md) also left a gap with no failure at all: a source
DAG that never runs never announces, and the transform silently never starts.

## Options considered
| Option | Problem |
|---|---|
| Airflow's own email (SMTP) | a mail account and an app password to configure; only reports failures, never "nothing ran" |
| A chat channel (Slack, Telegram) | a bot to set up; same blind spot for "nothing ran" |
| A heartbeat service (Healthchecks.io) | an outside dependency - but free, and one HTTP call |

## Decision
Healthchecks.io, one check, period 1 day, grace 2 hours. Its ping URL is the `HEALTHCHECK_URL`
environment variable on the Airflow host.

- Every task's failure callback posts the alert text to `<url>/fail`: an email within a minute.
- The transform DAG pings `<url>` after a green `dbt build`. No green build within 26 hours - a
  failed build, a paused DAG, a dead scheduler or host - is an email too. The absence of a
  signal is what gets reported, so it covers the failures that raise nothing.

## Consequences
- An ingestion failure emails at once; it does not stop the heartbeat, because the transform still
  runs on the other sources ([0015](0015-transform-when-ingestion-is-over.md)).
- The ping is best-effort: unset (local runs) means no ping, and an unreachable service is logged,
  never raised, so an alert cannot fail the task it reports on.
- If Healthchecks.io itself is down, no email arrives. Accepted for a personal project.
