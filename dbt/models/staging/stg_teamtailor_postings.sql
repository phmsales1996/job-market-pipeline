with source as (
    select * from {{ source('raw', 'teamtailor_postings')}}
),
workplace_map as (
    select * from {{ ref('workplace_type_map')}}
),
country_codes as (
    select * from {{ ref('country_codes') }}
),
renamed as (
    select
        'teamtailor' as source,
        id as source_job_id,
        title as title,
        url as job_url,
        first_seen_at as first_seen_at,
        last_seen_at as last_seen_at,
        s.remote_status as workplace_type_raw,
        wm.workplace_type as workplace_type,
        cc.country_code,
        s.country as country_raw,
        s.location as location_raw,
        s.role,
        s.department,
        s.published_at,
        nullif({{ html_to_text('s.content') }}, '') as description_text,
        s.company_slug
    from
        source s
    left join workplace_map wm on wm.source = 'teamtailor' and s.remote_status = wm.workplace_type_raw
    left join country_codes cc on cc.country_raw = trim(s.country)
)

select * from renamed