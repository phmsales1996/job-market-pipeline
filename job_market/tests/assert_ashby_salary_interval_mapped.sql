-- Every salary interval Ashby sends must be translated by the salary_interval_map seed.
-- Returns the rows where Ashby gave an interval but the seed had no match.
select
    source_job_id,
    salary_interval_raw
from {{ ref('stg_ashby_postings') }}
where salary_interval_raw is not null
  and salary_interval is null
