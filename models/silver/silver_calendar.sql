with latest as (
    {{ latest_version(source('bronze', 'calendar'), ['calendar_date']) }}
)

select
    cast(calendar_date as date)         as calendar_date,
    cast(iso_day_of_week as integer)    as iso_day_of_week,
    cast(is_holiday as boolean)         as is_holiday,
    cast(is_business_day as boolean)    as is_business_day
from latest
