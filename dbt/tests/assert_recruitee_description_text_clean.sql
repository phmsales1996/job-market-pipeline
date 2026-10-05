-- Counts the postings where something that looks like an HTML tag survives in Recruitee's
-- description_text. A WARNING, not an error: measured 2026-10-05, all 132 of 23,005 are text
-- the company pasted from Word or an XML editor, stored by Recruitee as escaped markup
-- (&lt;p&gt;). html_to_text strips real tags, then decodes entities - so the literal '<p>' a
-- visitor also sees on the job page comes through. Faithful to a messy source, not a macro
-- bug. Revisit when the macro learns "decode first, then strip" for Greenhouse. A jump well
-- above 132 would mean new markup the regex does not anticipate.
{{ config(severity='warn') }}
select
    source_job_id,
    regexp_extract(description_text, r'<[a-zA-Z/][^>]*>') as leftover_tag
from {{ ref('stg_recruitee_postings') }}
where regexp_contains(description_text, r'<[a-zA-Z/]')
