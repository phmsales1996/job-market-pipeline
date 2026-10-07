with source as (
    select * from {{ source('raw', 'greenhouse_postings')}}
),

located as (
    select 
        *,
        trim(array_reverse(split(regexp_replace(location, r'\s+-\s+|;|•', ','), ','))[safe_offset(0)]) as location_last_part
    from source
),
country_codes as (
    select * from {{ ref('country_codes') }}
),
us_states as (
    select * from {{ ref('us_states') }}
),

renamed as (
    select
        'greenhouse' as source,
        cast(id as STRING) as source_job_id,
        trim(title) as title,
        url as job_url,
        company,
        s.location as location_raw,
        coalesce(cc.country_code, if(us.state_raw is not null, 'US', null)) as country_code,
        cc.country_raw as country_raw,
        cast(null as string) as workplace_type_raw,
        case
            when regexp_contains(lower(location), r'remote') then 'remote'
            else 'unknown'
        end as workplace_type,
        s.department,
        language,
        first_seen_at as first_seen_at,
        last_seen_at as last_seen_at,
        s.published_at,
        s.updated_at,
        nullif({{ html_to_text(html_to_text('s.content')) }}, '') as description_text,
        s.company_slug
    from
        located s
    left join country_codes cc on cc.country_raw = trim(s.location_last_part) and (length(s.location_last_part) > 2 or s.location_last_part in ('US', 'UK'))
    left join us_states us on us.state_raw = s.location_last_part
)

select * from renamed