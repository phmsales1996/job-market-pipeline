-- Every salary period Recruitee sends must be translated by the salary_interval_map seed.
-- Returns the rows where Recruitee gave a period but the seed had no match: each one is a
-- word missing from seeds/salary_interval_map.csv - or a typo in the seed's source column,
-- which is how 1,057 hourly postings lost their interval on 2026-10-05 with a green build.
-- No salary period at all (both NULL) is fine.
select
    source_job_id,
    salary_period_raw
from {{ ref('stg_recruitee_postings') }}
where salary_period_raw is not null
  and salary_interval is null
