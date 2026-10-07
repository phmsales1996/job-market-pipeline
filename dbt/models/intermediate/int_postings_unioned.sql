with unioned as (
select source, source_job_id, company_slug, title, job_url, country_code, workplace_type, workplace_type_raw, description_text, published_at, first_seen_at, last_seen_at, location_raw, department, country_raw, salary_min, salary_max, salary_currency, salary_interval, cast(null as string) as language, cast(null as timestamp) as updated_at, employment_type
from {{ ref('stg_ashby_postings')}}

union all

select source, source_job_id, company_slug, title, job_url, country_code, workplace_type, workplace_type_raw, description_text, published_at, first_seen_at, last_seen_at, location_raw, department, country_raw, cast(null as numeric) as salary_min, cast(null as numeric) as salary_max, cast(null as string) as salary_currency, cast(null as string) as salary_interval, language, updated_at, cast(null as string) as employment_type
from {{ ref('stg_greenhouse_postings')}}

union all

select source, source_job_id, company_slug, title, job_url, country_code, workplace_type, workplace_type_raw, description_text, published_at, first_seen_at, last_seen_at, location_raw, team as department, cast(null as string) as country_raw, salary_min, salary_max, salary_currency, salary_interval, cast(null as string) as language, cast(null as timestamp) as updated_at, employment_type
from {{ ref('stg_lever_postings')}}

union all

select source, source_job_id, company_slug, title, job_url, country_code, workplace_type, workplace_type_raw, description_text, published_at, first_seen_at, last_seen_at, location_raw, department, country_raw, salary_min, salary_max, salary_currency, salary_interval, language, updated_at, employment_type
from {{ ref('stg_recruitee_postings')}}

union all

select source, source_job_id, company_slug, title, job_url, country_code, workplace_type, workplace_type_raw, description_text, published_at, first_seen_at, last_seen_at, location_raw, department, country_raw, cast(null as numeric) as salary_min, cast(null as numeric) as salary_max, cast(null as string) as salary_currency, cast(null as string) as salary_interval, cast(null as string) as language, cast(null as timestamp) as updated_at, cast(null as string) as employment_type
from {{ ref('stg_teamtailor_postings')}}

union all

select source, source_job_id, company_slug, title, job_url, country_code, workplace_type, workplace_type_raw, description_text, published_at, first_seen_at, last_seen_at, cast(null as string) as location_raw, department, country_raw, salary_min, salary_max, salary_currency, salary_interval, language, cast(null as timestamp) as updated_at, employment_type
from {{ ref('stg_workable_postings')}}
),

companies as (
    select * from {{ source('raw','companies') }}
)

select
    concat(u.source, '/', u.source_job_id) as posting_key,
    u.*,
    c.name as company_name
from
    unioned u
    left join companies c on u.company_slug = c.external_id and u.source = c.ats