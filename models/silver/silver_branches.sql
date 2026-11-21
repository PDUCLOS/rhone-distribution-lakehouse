with latest as (
    {{ latest_version(source('bronze', 'branches'), ['branch_id']) }}
)

select
    cast(branch_id as integer)  as branch_id,
    branch_code,
    branch_name,
    city,
    cast(postal_code as {{ dbt.type_string() }}) as postal_code,
    cast(opened_on as date)     as opened_on
from latest
