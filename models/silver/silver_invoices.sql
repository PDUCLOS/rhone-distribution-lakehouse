with latest as (
    {{ latest_version(source('bronze', 'invoices'), ['invoice_id'], 'updated_at desc, extracted_at') }}
),

orders as (
    select order_id from {{ ref('silver_orders') }}
)

select
    cast(latest.invoice_id as {{ dbt.type_bigint() }})      as invoice_id,
    latest.invoice_number,
    cast(latest.order_id as {{ dbt.type_bigint() }})        as order_id,
    cast(latest.customer_id as integer)                     as customer_id,
    cast(latest.invoice_date as date)                       as invoice_date,
    cast(latest.due_date as date)                           as due_date,
    cast(latest.amount_excl_tax as {{ dbt.type_numeric() }}) as amount_excl_tax,
    cast(latest.vat_amount as {{ dbt.type_numeric() }})     as vat_amount,
    latest.status,
    cast(latest.updated_at as {{ dbt.type_timestamp() }})   as updated_at,
    orders.order_id is null                                 as is_orphan
from latest
left join orders
    on cast(latest.order_id as {{ dbt.type_bigint() }}) = orders.order_id
