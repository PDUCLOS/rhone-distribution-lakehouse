with latest as (
    {{ latest_version(source('bronze', 'purchase_orders'), ['purchase_order_id']) }}
)

select
    cast(purchase_order_id as {{ dbt.type_bigint() }})  as purchase_order_id,
    cast(supplier_id as integer)                        as supplier_id,
    cast(product_id as integer)                         as product_id,
    cast(ordered_on as date)                            as ordered_on,
    cast(expected_on as date)                           as expected_on,
    cast(received_on as date)                           as received_on,
    cast(qty_ordered as integer)                        as qty_ordered,
    cast(unit_cost as {{ dbt.type_numeric() }})         as unit_cost
from latest
