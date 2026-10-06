-- Every salary frequency Workable sends must be translated by the salary_interval_map seed.
-- Returns the rows where Workable gave a frequency but the seed had no match: each one is a
-- word missing from seeds/salary_interval_map.csv (or a typo in the seed's source column).
-- Only 'year' is in the seed for Workable, on purpose: it was the only word seen when the
-- model was written (2026-10-05, 123 postings), so the first 'month' or 'hour' fails here.
-- No salary at all (both NULL) is fine.
select
    source_job_id,
    salary_interval_raw
from {{ ref('stg_workable_postings') }}
where salary_interval_raw is not null
  and salary_interval is null
