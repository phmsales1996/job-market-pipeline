# 0009. Workable: descriptions from the list request

Status: accepted, October 2026. Replaces the incremental detail fetch.

## Context
Workable's job list had no description; the text needed one more request per job. The first
design fetched details incrementally: only for jobs not yet held, capped per night, with a
circuit breaker so a rate-limit answer could not freeze a run.

After five nights, 650 of about 29,000 postings had a description.

## What the run logs showed
- The extract's own summary line: no details fetched, everything deferred, stopped early by
  the rate limit. The first detail request of the night was already refused.
- The refusal asked for a wait of several hours.
- The list requests, about 900 a night, were never refused. The limit is on the detail
  endpoint only.
- The good nights had fetched exactly 300 details.

## Decision
Ask for the description inside the list request, with a query parameter the list endpoint
accepts, and stop calling the detail endpoint.

## Why
- The arithmetic: about 300 details allowed per window against about 660 new postings a
  night. No schedule closes that gap, so re-timing the DAG or splitting it in two could not
  have worked.
- Checked at three sizes before trusting it: one job (the list's text was as long as the
  detail's three sections together), three boards (every job had its text), then a full run.

## Consequences
- Descriptions went from 2% to 95% of postings in one run. The rest had closed.
- Lost for now: salary, language and the precise workplace word, which only the detail has.
- The merge rule had to change with it. It used to update the description only from rows that
  carried a detail; with no details, every new description would have been discarded while
  the run stayed green.
- The detail code is kept, switched off, for a separate job that would fetch details for
  chosen postings within the allowance.
