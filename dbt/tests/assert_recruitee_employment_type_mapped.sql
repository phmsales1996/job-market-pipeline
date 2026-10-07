-- Every employment type Recruitee sends must be translated by the employment_type_map seed.
-- Returns the rows where the source gave a word but the seed had no match: a word missing
-- from seeds/employment_type_map.csv, a typo in the seed's source column, or a join looking
-- up another source's rows (it happened: 'ashby' left in the join of two other models
-- translated nothing, with a green build). No employment type at all (both NULL) is fine.
select
    source_job_id,
    employment_type_raw
from {{ ref('stg_recruitee_postings') }}
where employment_type_raw is not null
  and employment_type is null
