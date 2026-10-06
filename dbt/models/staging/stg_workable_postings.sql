with source as (
    select * from {{ source('raw', 'workable_postings')}}
),
workplace_map as (
    select * from {{ ref('workplace_type_map') }}
),
country_codes as (
    select * from {{ ref('country_codes') }}
),
salary_interval_map as (
    select * from {{ ref('salary_interval_map') }}
),
renamed as (
    select
        'workable' as source,
        id as source_job_id,
        title as title,
        url as job_url,
        first_seen_at as first_seen_at,
        last_seen_at as last_seen_at,
        workplace as workplace_type_raw,
        case
            when s.workplace is not null then wm.workplace_type
            when s.telecommuting is true then 'remote'
            else 'unknown'
        end as workplace_type,
        telecommuting,
        s.country_code as country_raw,
        cc.country_code,
        s.department,
        s.employment_type as employment_type_raw,
        s.experience,
        s.education,
        s.industry,
        s.job_function,
        s.language,
        timestamp(s.published_on) as published_at,
        s.salary_min,
        s.salary_max,
        s.salary_currency,
        s.salary_frequency as salary_interval_raw,
        sm.salary_interval,
        nullif({{ html_to_text('s.content') }}, '') as description_text
    from
        source s
    left join workplace_map wm on wm.source = 'workable' and s.workplace = wm.workplace_type_raw
    left join salary_interval_map sm on sm.source = 'workable' and s.salary_frequency = sm.salary_interval_raw
    left join country_codes cc on cc.country_raw = trim(s.country_code)
)


select * from renamed
