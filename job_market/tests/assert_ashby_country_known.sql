-- Every country value Ashby sends must be KNOWN to the country_codes seed - either mapped to
-- a code, or listed there deliberately with no code (regions such as 'Europe').
-- "Known" is checked against the seed itself, not by country_code being NULL: a NULL code is
-- legitimate for a known region. Fix a failure by re-running scripts/generate_country_seed.py
-- (and adding an alias or a not-a-country entry there if it still doesn't match).
select
    stg.source_job_id,
    stg.country_raw
from {{ ref('stg_ashby_postings') }} as stg
left join {{ ref('country_codes') }} as seed
    on seed.country_raw = trim(stg.country_raw)
where stg.country_raw is not null
  and seed.country_raw is null
