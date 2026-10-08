-- Each mapping seed must have one row per key. A duplicate key makes every staging join that
-- uses the seed match twice - silently duplicating postings (it happened once: the Ashby
-- workplace rows were added twice).
select 'workplace_type_map' as seed, source || ' / ' || workplace_type_raw as key, count(*) as n
from {{ ref('workplace_type_map') }}
group by 1, 2
having count(*) > 1

union all

select 'salary_interval_map', source || ' / ' || salary_interval_raw, count(*)
from {{ ref('salary_interval_map') }}
group by 1, 2
having count(*) > 1

union all

select 'country_codes', country_raw, count(*)
from {{ ref('country_codes') }}
group by 1, 2
having count(*) > 1

union all

select 'us_states', state_raw, count(*)
from {{ ref('us_states') }}
group by 1, 2
having count(*) > 1

union all

select 'employment_type_map', source || ' / ' || employment_type_raw, count(*)
from {{ ref('employment_type_map') }}
group by 1, 2
having count(*) > 1

union all

select 'countries', country_code, count(*)
from {{ ref('countries') }}
group by 1, 2
having count(*) > 1
