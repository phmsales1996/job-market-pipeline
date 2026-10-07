with source as (
    select * from {{ source('raw', 'recruitee_postings') }}
),
country_codes as (
    select * from {{ ref('country_codes') }}
),
salary_interval_map as (
    select * from {{ ref('salary_interval_map') }}
),
employment_type_map as (
    select * from {{ ref('employment_type_map') }}
),
renamed as (
    select
        'recruitee' as source,
        cast(s.id as STRING) as source_job_id,
        s.title,
        s.language,
        s.url as job_url,
        cc.country_code,
        nullif(trim(s.country_code), '') as country_raw, 
        s.first_seen_at,
        s.last_seen_at,
        case
            when s.remote is true then 'remote'
            when s.hybrid is true then 'hybrid'
            when s.on_site is true then 'in_person'
            else 'unknown'
        end as workplace_type,
        nullif(array_to_string([
            case when s.remote is true then 'remote' else null end,
            case when s.hybrid is true then 'hybrid' else null end,
            case when s.on_site is true then 'on_site' else null end
            ], '-'),'') as workplace_type_raw,
        s.location as location_raw,
        s.department,
        s.employment_type as employment_type_raw,
        em.employment_type,
        s.published_at,
        s.updated_at,
        s.salary_min,
        s.salary_max,
        s.salary_currency,
        s.salary_period as salary_period_raw,
        sm.salary_interval,
        {{ html_to_text('s.highlight') }} as highlight_text,
        {{ html_to_text('s.content') }} as content_text,
        {{ html_to_text('s.requirements') }} as requirements_text,
        s.company_slug
    from source s
    left join salary_interval_map sm on sm.source = 'recruitee' and sm.salary_interval_raw = s.salary_period
    left join country_codes cc on cc.country_raw = trim(s.country_code)
    left join employment_type_map em on em.source = 'recruitee' and em.employment_type_raw = s.employment_type
),

assembled as (
    select
        * except (highlight_text, content_text, requirements_text),
        nullif(array_to_string([
            nullif(highlight_text, ''),
            nullif(content_text, ''),
            nullif(requirements_text, '')
        ], '\n\n'), '') as description_text
    from renamed
)


select * from assembled
