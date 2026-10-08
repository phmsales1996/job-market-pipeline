# 0002. One DAG per source, on staggered schedules

Status: accepted, September 2026. The transform DAG it anticipates is not built yet.

## Context
The sources differ a lot in size and behaviour: a few hundred boards for one, about 1,500 for
another; one answers in under a second, another rate-limits. A single DAG looping over all
sources would tie their fates together.

## Decision
Each source has its own DAG with the same three tasks, `extract >> load >> check`, started an
hour apart during the night. The shared behaviour lives in one module per step; a source
supplies only what differs (how to fetch one board, how to flatten one posting).

## Why
- A failure or a slow night in one source does not delay or fail the others.
- Timeouts and retries can be set per source from its own measured run times.
- A source can be re-run alone.

## Consequences
- Six small DAG files that look alike. That repetition is accepted: the logic they call is
  shared, and the files hold only the schedule and the wiring.
- The dbt models are not scheduled yet. The plan is a transform DAG triggered when the
  ingestion DAGs finish, rather than a fixed clock time that assumes they have.
