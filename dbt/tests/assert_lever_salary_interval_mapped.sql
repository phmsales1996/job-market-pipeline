-- Every salary interval Lever sends must be translated by the salary_interval_map seed.
-- Returns the rows where Lever gave an interval but the seed had no match: each one is a
-- word missing from seeds/salary_interval_map.csv. No salary at all (both NULL) is fine.
select
    source_job_id,
    salary_interval_raw
from {{ ref('stg_lever_postings') }}
where salary_interval_raw is not null
  and salary_interval is null
