with source as (
    select * from {{ source('raw', 'ashby_postings') }}
),
workplace_map as (
    select * from {{ ref('workplace_type_map') }}
),
salary_interval_map as (
    select * from {{ ref('salary_interval_map') }}
),
country_codes as (
    select * from {{ ref('country_codes') }}
),
renamed as (
    select
        'ashby' as source,
        s.id as source_job_id,
        s.title,
        s.url as job_url,
        -- Country names are shared across sources, so this join has no source key.
        cc.country_code,
        nullif(trim(s.country), '') as country_raw,     -- 45 postings send '' for no country
        s.first_seen_at,
        s.last_seen_at,
        s.workplace_type as workplace_type_raw,
        -- Ashby says nothing for ~10% of postings: that is 'unknown'. An unmapped *word*
        -- still comes out NULL, so the not_null test keeps catching it.
        case
            when s.workplace_type is null then 'unknown'
            else wm.workplace_type
        end as workplace_type,
        s.location as location_raw,
        s.department,
        s.team,
        s.published_at,
        s.salary_min,
        s.salary_max,
        s.salary_currency,
        s.salary_interval as salary_interval_raw,
        sm.salary_interval,
        s.compensation_summary,
        -- Already plain text: the loader stores Ashby's descriptionPlain.
        nullif(trim(s.content), '') as description_text,
        s.company_slug
    from source s
    left join workplace_map wm on wm.source = 'ashby' and wm.workplace_type_raw = s.workplace_type
    left join salary_interval_map sm on sm.source = 'ashby' and sm.salary_interval_raw = s.salary_interval
    left join country_codes cc on cc.country_raw = trim(s.country)
)
select * from renamed
