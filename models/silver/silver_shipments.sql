with latest as (
    {{ latest_version(source('bronze', 'shipments'), ['shipment_id']) }}
)

select
    cast(shipment_id as {{ dbt.type_bigint() }})    as shipment_id,
    cast(order_id as {{ dbt.type_bigint() }})       as order_id,
    cast(order_date as date)                        as order_date,
    cast(shipped_on as date)                        as shipped_on,
    cast(delivered_on as date)                      as delivered_on,
    carrier,
    cast(shipped_on as date) < cast(order_date as date) as is_shipped_before_order
from latest
