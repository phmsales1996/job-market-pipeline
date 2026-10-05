-- No HTML tag may survive into Lever's description_text: html_to_text strips every tag, so a
-- leftover means markup the regex did not anticipate. Entities are not checked here - a few
-- double-escaped ones survive by design (measured 2026-10-04: 6 of 16,486 postings).
select
    source_job_id,
    regexp_extract(description_text, r'<[a-zA-Z/][^>]*>') as leftover_tag
from {{ ref('stg_lever_postings') }}
where regexp_contains(description_text, r'<[a-zA-Z/]')
