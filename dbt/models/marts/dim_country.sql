select
    country_code,
    country_name,
    region,
    sub_region,
    business_region
from {{ ref('countries')}}

union all

select 'ZZ', 'Unknown', 'Unknown', 'Unknown', 'Unknown'