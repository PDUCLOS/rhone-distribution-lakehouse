with latest as (
    {{ latest_version(source('bronze', 'suppliers'), ['supplier_id']) }}
)

select
    cast(supplier_id as integer)                        as supplier_id,
    supplier_name,
    country_code,
    cast(standard_lead_time_days as integer)            as standard_lead_time_days,
    cast(reliability_score as {{ dbt.type_float() }})   as reliability_score
from latest
