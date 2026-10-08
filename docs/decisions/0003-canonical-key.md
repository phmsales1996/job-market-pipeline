# 0003. A posting is identified by source plus the source's id

Status: accepted, October 2026

## Context
Source ids come in different types: integers for two sources, UUIDs or short codes for the
others. Two sources can use the same id for different postings.

## Decision
- In staging, every source's id becomes text, in a column named `source_job_id`, next to a
  literal `source`.
- The pair is the key. Where one column is needed, the two are joined with a slash into
  `posting_key`, for example `lever/4f2a...`.

## Why
- Stacking the sources needs one type per column; text holds every id.
- dbt's `unique` test looks at one column. A single key column turns "no posting was
  doubled" into a test that runs on every build.

## Consequences
- The key is readable, and long. A hashed surrogate key was considered and left for when a
  mart needs it.
- `posting_key` being unique is the guard on every join added after the union. A join on a
  half-key would have doubled postings; this test is what would catch it.
