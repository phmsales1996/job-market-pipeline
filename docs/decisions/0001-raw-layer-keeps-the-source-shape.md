# 0001. The raw layer keeps each source's shape and words

Status: accepted, September 2026

## Context
Six job-board APIs describe the same thing in six ways. Lever says `Full-Time` and Ashby
`FullTime`; one sends a country code, another a country name, another nothing. The first
question was where the translation into one model should happen.

## Decision
Nothing is interpreted before the warehouse.
- The API response is stored byte for byte in object storage, before any parsing.
- Each source has its own raw table, with its own column meanings, holding one row per
  posting (current state, upserted with `MERGE`), plus the complete original payload as text.
- Only what the pipeline itself guarantees is `NOT NULL`: the id, the payload and the
  pipeline's timestamps. Everything the source provides may be empty.
- Translation into shared names and values happens once, downstream, in dbt.

## Why
- A `NOT NULL` on someone else's API is a promise that eventually breaks. Completeness is
  reported as a fill rate per column on every run instead of blocking the load.
- Keeping the whole payload means a field that was not flattened can be recovered without
  fetching again. Several later decisions relied on this.
- Interpreting in six loaders would have put six copies of every rule in Python, outside
  the tests and lineage that dbt gives.

## Consequences
- The raw tables are not comparable with each other. That is the staging layer's job.
- The raw table is current state, not history: a posting has one row, with `first_seen_at`
  and `last_seen_at`. Landed files are deleted after 7 days, so the table is the only
  long-term record. Keeping history is still open work.
