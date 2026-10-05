with source as (
    select * from {{ source('raw', 'lever_postings')}}
),
workplace_map as (
    select * from {{ ref('workplace_type_map')}}
),
salary_interval_map as (
    select * from {{ ref('salary_interval_map')}}
),
renamed as (
    select
        'lever' as source,
        id as source_job_id,
        title as title,
        url as job_url,
        country as country_code,
        first_seen_at as first_seen_at,
        last_seen_at as last_seen_at,
        s.workplace_type as workplace_type_raw,
        wm.workplace_type as workplace_type,
        location as location_raw,
        department as team,
        published_at as published_at,
        salary_min as salary_min,
        salary_max as salary_max,
        salary_currency as salary_currency,
        s.salary_interval as salary_interval_raw,
        sm.salary_interval as salary_interval,
        -- Lever's `lists`: titled sections (often the requirements), HTML only - no plain
        -- twin. Unpack the array, clean each section, pack it back into one string, in order.
        (
            select string_agg(
                concat(
                    json_value(item, '$.text'), ': ',
                    {{ html_to_text("json_value(item, '$.content')") }}
                ),
                '\n\n' order by pos
            )
            from unnest(json_query_array(s.raw, '$.lists')) as item with offset as pos
        ) as lists_text,
        -- The other three pieces, converted from HTML too: Lever's plain-text twins are blank
        -- for ~half the postings even when the HTML has a full description.
        {{ html_to_text("json_value(s.raw, '$.opening')") }} as opening_text,
        {{ html_to_text('s.content') }} as body_text,
        {{ html_to_text('s.additional') }} as additional_text
    from
        source s
    left join workplace_map wm on wm.source = 'lever' and s.workplace_type = wm.workplace_type_raw
    left join salary_interval_map sm on sm.source = 'lever' and sm.salary_interval_raw = s.salary_interval
),

assembled as (
    select
        * except (opening_text, body_text, additional_text),
        -- One text in posting order. array_to_string skips NULL elements; nullif turns a
        -- piece that is empty after cleaning ('') into NULL so it is skipped too, instead of
        -- leaving a stray blank line.
        nullif(array_to_string([
            nullif(opening_text, ''),
            nullif(body_text, ''),
            lists_text,
            nullif(additional_text, '')
        ], '\n\n'), '') as description_text
    from renamed
)

select * from assembled