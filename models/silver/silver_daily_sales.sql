-- Daily sales at the extract grain. A day re-extracted in a later batch
-- replaces the earlier version (late corrections).
with latest as (
    {{ latest_version(source('bronze', 'daily_sales'),
                      ['sale_date', 'customer_id', 'product_id', 'branch_id', 'rep_id', 'channel']) }}
),

typed as (
    select
        cast(sale_date as date)                         as sale_date,
        cast(customer_id as integer)                    as customer_id,
        cast(product_id as integer)                     as product_id,
        cast(branch_id as integer)                      as branch_id,
        cast(rep_id as integer)                         as rep_id,
        channel,
        cast(order_count as integer)                    as order_count,
        cast(line_count as integer)                     as line_count,
        cast(coalesce(qty_ordered, 0) as integer)       as qty_ordered,
        cast(coalesce(qty_shipped, 0) as integer)       as qty_shipped,
        cast(coalesce(qty_returned, 0) as integer)      as qty_returned,
        cast(net_amount as {{ dbt.type_numeric() }})    as net_amount,
        cast(cost_amount as {{ dbt.type_numeric() }})   as cost_amount,
        cast(coalesce(ordered_amount, 0) as {{ dbt.type_numeric() }}) as ordered_amount,
        cast(extracted_at as {{ dbt.type_timestamp() }}) as extracted_at
    from latest
)

select
    *,
    -- ordered_amount excludes returns: a sale cancelled by a same-day return is not a pricing defect
    qty_ordered > 0 and ordered_amount = 0      as is_zero_price,
    qty_shipped < 0 and qty_returned = 0        as is_unflagged_negative_qty
from typed
