with latest as (
    {{ latest_version(source('bronze', 'products'), ['product_id']) }}
)

select
    cast(product_id as integer)                         as product_id,
    sku,
    product_name,
    product_family,
    sales_unit,
    cast(list_price_2024 as {{ dbt.type_numeric() }})   as list_price_2024,
    cast(unit_cost_2024 as {{ dbt.type_numeric() }})    as unit_cost_2024,
    cast(supplier_id as integer)                        as supplier_id,
    cast(is_active as boolean)                          as is_active
from latest
