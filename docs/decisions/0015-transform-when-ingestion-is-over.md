# 0015. The transform runs when ingestion is over, not at a time

Status: accepted, October 2026

## Context
The dbt models were rebuilt by hand. The six ingestion DAGs start an hour apart and the last one
ends at a time that varies by tens of minutes from night to night. In four days, five new values
failed dbt tests and were only noticed because someone happened to run a build.

## Options considered
| Trigger for the transform | Problem |
|---|---|
| A fixed time, after the usual end | a slow source makes it build on half-loaded data; nothing says so |
| All six sources succeeded | one failed source blocks the build for all six |
| Any source succeeded | six builds a night, most of them on incomplete data |
| A chain, each source starting the next | couples the sources, which [0002](0002-one-dag-per-source.md) chose not to do: one hung run would stop the night |

## Decision
The transform DAG is scheduled on six Airflow assets, one per source, and runs once all six have
been announced. Each ingestion DAG ends with a task that announces "this source is over for
tonight", whether the run succeeded or failed.

- That last task is a **teardown**: it runs after a failure too, and it is ignored when the run's
  state is decided, so a failed run is still marked failed.
- The asset names are defined once and imported by both sides. Two DAGs meet only through the
  name, and a name spelled differently on each side would not fail: the transform would wait
  forever.

## Why it is safe to build with one stale source
Open-or-closed is worked out per source ([0014](0014-open-or-closed.md)), so a source without a
new run keeps its postings open rather than closing them all. The source-freshness check reports
the stale table.

## Consequences
- One build per night, starting when the last source ends.
- A source DAG that never runs at all - paused, or the scheduler down - never announces, and the
  transform does not start. Nothing fails. This needs a "nothing ran" alert, which is not built.
- dbt runs on the Airflow host in its own virtual environment, because it and Airflow pin many
  of the same libraries at different versions.
- A failing test is not retried: it would fail again, and retrying only delays the alert.
