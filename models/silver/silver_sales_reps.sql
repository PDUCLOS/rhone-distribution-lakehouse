with latest as (
    {{ latest_version(source('bronze', 'sales_reps'), ['rep_id']) }}
)

select
    cast(rep_id as integer)     as rep_id,
    cast(branch_id as integer)  as branch_id,
    first_name,
    last_name,
    cast(hired_on as date)      as hired_on
from latest
