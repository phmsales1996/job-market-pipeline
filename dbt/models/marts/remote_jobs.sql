with jobs as (
    select * from {{ ref('fct_job_postings')}}
),
countries as (
    select * from {{ ref('dim_country')}}
)
select
    j.posting_key,
    j.title,
    j.company_name,
    c.country_name,
    c.business_region,
    j.employment_type,
    j.salary_min, 
    j.salary_max, 
    j.salary_currency, 
    j.salary_interval, 
    j.job_url, 
    j.source, 
    j.published_at, 
    j.last_seen_at
from
    jobs j
    join countries c on j.country_key = c.country_code
where
    j.workplace_type = 'remote' and j.is_open