with int_postings_unioned as (
    select * from {{ ref('int_postings_unioned')}}
),
source_freshness as (
    select
        source,
        max(last_seen_at) as source_last_seen_at
    from
        int_postings_unioned
    group by source
)

select
    posting_key,
    iu.source,
    title,
    coalesce(country_code, 'ZZ') as country_key,
    source_job_id,
    company_slug,
    company_name,
    job_url,
    workplace_type,
    employment_type,
    department,
    language,
    location_raw,
    salary_min,
    salary_max,
    salary_currency,
    salary_interval,
    description_text,
    published_at,
    updated_at,
    first_seen_at,
    last_seen_at,
    cast(iu.last_seen_at as date) = cast(sf.source_last_seen_at as date)  as is_open
from
    int_postings_unioned iu
    join source_freshness sf on iu.source = sf.source