-- Every country code Workable sends must be KNOWN to the country_codes seed. Workable already
-- sends ISO codes, so "known" means the seed lists that code as its own identity row.
-- Checked against the seed itself, not by country_code being NULL: a posting with no country
-- is legitimate, a code nobody has heard of is not. Fix a failure by looking at the value
-- first (a typo? lowercase? a new territory?), then re-running scripts/generate_country_seed.py.
select
    stg.source_job_id,
    stg.country_raw
from {{ ref('stg_workable_postings') }} as stg
left join {{ ref('country_codes') }} as seed
    on seed.country_raw = trim(stg.country_raw)
where stg.country_raw is not null
  and seed.country_raw is null
