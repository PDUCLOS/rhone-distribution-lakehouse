with latest as (
    {{ latest_version(source('bronze', 'orders'), ['order_id'], 'updated_at desc, extracted_at') }}
)

select
    cast(order_id as {{ dbt.type_bigint() }})       as order_id,
    order_number,
    cast(customer_id as integer)                    as customer_id,
    cast(branch_id as integer)                      as branch_id,
    cast(rep_id as integer)                         as rep_id,
    channel,
    cast(order_date as date)                        as order_date,
    status,
    cast(created_at as {{ dbt.type_timestamp() }})  as created_at,
    cast(updated_at as {{ dbt.type_timestamp() }})  as updated_at
from latest
